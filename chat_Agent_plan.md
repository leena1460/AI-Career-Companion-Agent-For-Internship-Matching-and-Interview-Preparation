# Conversational Career Agent — Implementation Plan

A conversational career assistant endpoint (`POST /chat`) that greets the
authenticated user by name, understands their career/internship/interview-prep
questions, routes each turn to the right existing service via an intent-router,
and returns a natural reply. Conversation history is persisted per user.

## Decisions

- **Framework**: LangGraph + LangChain. `langgraph` is a **new dependency**
  (`uv add langgraph`); `langchain-ollama` is already installed.
- **Dispatch**: intent-router approach — a first structured-extraction call
  classifies intent, we dispatch to an existing service, then a second plain
  chat call composes the reply.
- **History window**: last **5** messages per conversation (older rows stay in
  DB for retrieval/display).
- **Reuse existing services as tools** — no business logic duplication:
  `MatchingOrchestrator`, `SkillGapService`, `InterviewPrepService`,
  `InternshipRetriever`.

## High-level flow

```
POST /chat  (router-level get_current_user → user_id)
   ↓
ConversationService.chat(user_id, message, conversation_id?)
   ↓
CareerContextService.build(user_id)
   ├─ UserRepository.get_by_id → User.name + UserProfile.skills/location_preference
   └─ UserDetailRepository.list_by_user(RESUME)[0] → latest resume
   ↓  → CareerContext{name, skills, location_preference, resume{...}}
ConversationRepository.get_or_create(user_id, conversation_id)
ConversationRepository.list_recent(conversation_id, limit=5) → history
   ↓
CareerAgent.run(message, context, history)        # LangGraph state machine
   ├─ intent_router node → IntentDecision{intent, args}  (json_schema extraction)
   ├─ dispatch node      → tool call (or none)
   │     ├─ find_jobs    → InternshipRetriever.search(query, filters)
   │     ├─ match        → MatchingOrchestrator.match(user_id, MatchingRequest(...))
   │     ├─ skill_gap    → SkillGapService.analyze(user_id, job_id, user_detail_id)
   │     ├─ interview    → InterviewPrepService.prepare(job_id, instructions)
   │     └─ greet/general→ no tool
   └─ compose node       → ChatOllama (plain chat) with system prompt + context
                           + history + tool result → natural reply
   ↓  → reply text
ConversationRepository.add_message(conversation_id, user_message, ai_response)
   ↓
ChatResponse{conversation_id, reply, intent, tool_used?}
```

The **greeting** is model-driven via the system prompt: "On the first turn
(empty history), greet the user by name using CareerContext.name." No
hardcoded branch. No fabrication — if a tool needs a resume and none exists,
the agent tells the user to upload one.

## File structure (new files only)

```
app/
├── models/
│   └── conversation.py                       # Conversation + ChatMessage ORM
├── schemas/
│   └── conversation.py                       # ChatRequest, ChatResponse, CareerContext, IntentDecision
├── database/repositories/
│   └── conversation_repository.py            # create/get conversation, add_message, list_recent(limit=5)
├── services/
│   ├── career_context_service.py             # build CareerContext from user+profile+latest resume
│   └── conversation_service.py               # endpoint orchestrator
├── agents/
│   ├── career_agent.py                       # LangGraph StateGraph: intent_router → dispatch → compose
│   └── career_tools.py                       # 4 thin wrappers around existing services/retriever
├── api/
│   └── conversations.py                      # POST /chat (router-level auth)
migrations/versions/
└── 20260815_0005_create_conversations.py     # conversations + chat_messages tables
tests/
├── api/test_conversations.py
├── agents/test_career_agent.py
└── services/test_career_context_service.py
```

**Wiring** (per AGENTS.md 4-layer convention): export `chat_router` in
`app/api/__init__.py`, add `get_conversation_service` +
`get_career_context_service` + `get_career_agent` providers in
`app/api/dependencies.py`, `app.include_router(chat_router)` in `app/main.py`.

## Database schema (new migration)

```sql
CREATE TABLE conversations (
    id           UUID PRIMARY KEY,
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(16) NOT NULL,   -- 'user' | 'assistant'
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_chat_messages_conv_created ON chat_messages (conversation_id, created_at);
```

## The four tools (`app/agents/career_tools.py`)

Thin async wrappers; no business logic duplicated.

| Tool | Intent | Backed by (existing) | Args | Resume? |
|---|---|---|---|---|
| `job_search` | `find_jobs` | `InternshipRetriever.search(query, filters={"location":...})` (in `asyncio.to_thread`) | `query`, `location?` | No |
| `match_jobs` | `match` | `MatchingOrchestrator.match(user_id, MatchingRequest(user_detail_id=latest_resume_id))` | `job_id?` (optional) | Yes — auto-pick latest |
| `skill_gap` | `skill_gap` | `SkillGapService.analyze(user_id, job_id, user_detail_id=latest_resume_id)` | `job_id` | Yes — auto-pick latest |
| `interview_prep` | `interview_prep` | `InterviewPrepService.prepare(job_id, instructions)` | `job_id`, `instructions?` | No |

**Resume selection rule**: auto-select
`UserDetailRepository.list_by_user(user_id, DocumentType.RESUME)[0]` (newest
first — confirmed in repo). If none exists, the tool returns a "no resume"
sentinel and the compose node tells the user to upload one — never fabricate.

## LangGraph agent (`app/agents/career_agent.py`)

Three-node `StateGraph`:

- **`intent_router`** — uses the proven `StructuredExtractionClient` with
  `with_structured_output(IntentDecision, method="json_schema")` to classify
  into `{intent, job_id?, query?, location?, instructions?}`. Six intents:
  `greet`, `find_jobs`, `match`, `skill_gap`, `interview_prep`, `general`.
  **Apply the AGENTS.md field-name-contract fix** to the router prompt
  (explicit keys + example) to handle `gpt-oss:120b-cloud` drift.
- **`dispatch`** — pure-Python if/else on `intent` → calls the matching tool
  in `career_tools.py` (or none for `greet`/`general`). Result stored in
  state as `tool_result`.
- **`compose`** — plain `ChatOllama` (NOT structured output — free text) with:
  system prompt (career-coach persona + "greet by name on first turn" rule) +
  `CareerContext` JSON + last 5 `ChatMessage`s + tool result (if any) → returns
  the natural reply.

Edges: `intent_router → dispatch → compose`. Terminal at `compose`. This keeps
the **structured extraction path (validated) for routing** and uses plain chat
for the reply (no schema drift risk on free text).

## Schemas (`app/schemas/conversation.py`)

- `ChatRequest { message: str, conversation_id: UUID | None }`
- `ChatResponse { conversation_id: UUID, reply: str, intent: str, tool_used: str | None }`
- `CareerContext { name, skills: list[str], location_preference: str|None, resume: dict | None }`
  (resume = subset of `UserDetail` fields)
- `IntentDecision { intent: Literal[...], job_id: UUID|None, query: str, location: str|None, instructions: str }`
  (the router's structured output schema)

## Dependency providers (`app/api/dependencies.py`)

```python
def get_career_context_service(db) -> CareerContextService: ...   # UserRepository + UserDetailRepository
def get_career_agent(settings) -> CareerAgent: ...                 # ChatOllama + StructuredExtractionClient
def get_conversation_service(db, settings, context_service, agent) -> ConversationService: ...
```

## Testing strategy (mirrors existing patterns)

- **`tests/api/test_conversations.py`** — `TestClient` on minimal `FastAPI()`;
  override `get_current_user` + `get_conversation_service` with `AsyncMock`.
  Assert 401 without auth, 200 with mocked reply, conversation_id round-trips.
- **`tests/agents/test_career_agent.py`** — mock the intent-router extractor +
  the 4 tool wrappers; assert correct dispatch per intent, and that
  `greet`/`general` skip tools. Assert compose node receives tool result in
  state.
- **`tests/services/test_career_context_service.py`** — mock
  `UserRepository.get_by_id` + `UserDetailRepository.list_by_user`; assert
  `CareerContext` merges profile skills + resume skills (casefold-dedup like
  `_merge_skills`), and handles no-resume case (resume=None).
- All tests **fully mocked** — no Postgres, Ollama, or Chroma (per AGENTS.md).

## LLM / cloud-model gotcha (already accounted for)

Per AGENTS.md: `gpt-oss:120b-cloud` drifts on `json_schema` field names. The
**intent-router** node uses structured output, so its `IntentDecision` schema +
prompt will include the explicit field-name contract + worked example (the
proven fix pattern). The **compose** node uses plain chat (no schema) so it's
unaffected.

## New dependency

```powershell
uv add langgraph
```

The only new external package. `langchain-ollama` is already installed
(provides `ChatOllama` + `bind_tools`).

## Greenfield vs reused

| Aspect | Status |
|---|---|
| Conversation/Message persistence | **New** (model + repo + migration) |
| CareerContext builder | **New** (but reuses `UserRepository` + `UserDetailRepository`) |
| Career agent (LangGraph) | **New** |
| 4 tools | **New wrappers**, but call existing services/retriever unchanged |
| Matching / Skill gap / Interview prep / Retriever | **Reused as-is** |
| Auth | **Reused** (`get_current_user`) |

## Build order

1. `uv add langgraph`
2. `app/models/conversation.py` + migration + `ConversationRepository`
3. `app/schemas/conversation.py`
4. `app/services/career_context_service.py`
5. `app/agents/career_tools.py`
6. `app/agents/career_agent.py` (LangGraph graph)
7. `app/services/conversation_service.py`
8. `app/api/conversations.py` + wiring (`__init__.py`, `dependencies.py`, `main.py`)
9. Tests (agent, service, api)
10. `ruff check` + `pytest`