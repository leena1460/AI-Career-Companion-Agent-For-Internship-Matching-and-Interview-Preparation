# AGENTS.md

Compact guidance for OpenCode sessions working in this repo. The README covers
setup, API tables, and run commands — read it first. This file captures what the
README and filenames do **not** make obvious.

## Source of truth

- `.cursor/skills/internship-matching-platform/SKILL.md` is the architecture /
  scope source of truth (target dir tree, module list, coding standards, auth
  policy). Read it before generating or editing any code. It is slightly stale:
  it lists `interview-prep` as "Not started", but `POST /interview-prep` is now
  implemented (`app/api/interview_prep.py` + agent/service/schema). Trust the
  code over SKILL.md when they conflict.

## Commands

```powershell
uv sync                              # install deps
uv run alembic upgrade head          # apply DB migrations (needs local Postgres)
uv run python -m uvicorn app.main:app --reload   # dev server → http://127.0.0.1:8000/docs
uv run pytest                        # full suite
uv run pytest tests/api/test_interview_prep.py -v   # single file
uv run pytest tests/agents/test_interview_prep_agent.py::TestInterviewPrepAgent::test_prunes_blank_rows_and_renumbering_steps  # single test
```

Lint/format (Windows venv binaries also work without `uv run`):

```powershell
.venv\Scripts\ruff.exe check app/ tests/        # select = E,F,I,UP ; line-length 100
.venv\Scripts\ruff.exe check --fix <files>      # auto-fix import sort (I001)
.venv\Scripts\ruff.exe format <files>           # black-compatible formatter
```

There is no typecheck step configured (no mypy config). Verify changes with
`ruff check` + `pytest`.

**Repo lint state:** several pre-existing files (e.g. `cover_letter_agent.py`,
`cover_letter_tailoring_service.py`, `tests/agents/test_cover_letter_agent.py`)
already exceed `E501`. Do not attempt a repo-wide lint cleanup unless asked;
just keep **new/edited** files clean.

## Agent endpoint pattern (4 layers)

Every LLM-driven business endpoint follows the same wiring. Mirror the closest
existing analog, not a generic FastAPI tutorial.

| Layer | File | Analog for JSON endpoints |
| --- | --- | --- |
| Schemas | `app/schemas/<name>.py` | `skill_gap.py` / `interview_prep.py` |
| Agent | `app/agents/<name>_agent.py` | `skill_gap_agent.py` / `interview_prep_agent.py` |
| Service | `app/services/<name>_service.py` | `skill_gap_service.py` / `interview_prep_service.py` |
| API | `app/api/<name>.py` | `skill_gaps.py` / `interview_prep.py` |

Then wire: export the router in `app/api/__init__.py`, add a
`get_<name>_service` provider in `app/api/dependencies.py`, and
`app.include_router(...)` in `app/main.py`.

Conventions enforced across all layers:

- **Type hints everywhere**; Pydantic models cross every API/LLM boundary.
- **Auth**: protect new business endpoints with `get_current_user` from
  `app.auth.dependencies` (router-level dependency preferred). Never accept a
  `user_id` from the client — ownership comes from the access-token cookie.
- **LLM contract**: agents depend on the `StructuredExtractionClient`
  abstraction (`app/llm/client.py`), never on `ChatOllama` directly. Inject an
  `OllamaStructuredExtractionClient` from the dependency provider. Output is
  schema-constrained via `with_structured_output(schema, method="json_schema")`.
- **Pruning**: every agent calls a `prune_*_result()` helper in its schema
  module to drop blank rows / normalize fields after LLM extraction. Do not
  return raw LLM output.
- **Multipart "exactly one of" pattern**: endpoints that take a resume accept
  either an uploaded `file` **or** a `user_detail_id`, never both/none. Enforce
  with `has_upload == (selected_detail_id is not None)` → 422.
- **Errors**: domain exceptions (`ResourceNotFoundError`, `ResourceAccessDeniedError`,
  `DocumentParsingError`, etc. in `app/core/exceptions.py`) are mapped to HTTP
  statuses in the API layer, not raised directly as `HTTPException` from services.

## Config / environment gotchas

- `app/core/config.py` is the executable source of truth for settings. Note
  the default `ollama_chat_model` is `gpt-oss:120b-cloud` (the README mentions
  `granite4.1:8b` for local pulls — that is for an alternative local setup;
  the running default is the cloud model). `mxbai-embed-large` is the embedding
  model used by `app/rag/embeddings.py`.
- `get_settings()` is `@lru_cache`d — tests that need to override settings must
  use `get_settings.cache_clear()` or dependency override, not env mutation
  mid-process.
- App startup runs `init_db()` (SQLAlchemy `create_all`) **and** Alembic
  migrations exist. If the DB was first created via `create_all`, mark Alembic
  baseline with `uv run alembic stamp head` (see README) before running new
  migrations, or Alembic will think nothing is applied.

## LLM / cloud-model gotcha (important)

The default `ollama_chat_model` is `gpt-oss:120b-cloud`, a **cloud-routed**
 model (`remote_host: https://ollama.com`, visible in `ollama list`).
Unlike local GGUF models, cloud models treat Ollama's `format=json_schema`
as **loose guidance** and may rename fields or merge semantically-similar
keys, producing valid JSON that fails Pydantic validation.

Confirmed drift on `gpt-oss:120b-cloud` (caused a 502 on `POST /interview-prep`):
- `focus_areas` items emitted `subject` instead of the required `topic`.
- `technical_questions` items put the question text in `topic` and **omitted**
  the required `question` field entirely.

The blanket `except Exception` in `app/llm/client.py:extract()` maps any such
`ValidationError` to a generic
`"could not produce the required structured document response"` 502 that hides
the real cause. When debugging a 502 from an agent endpoint, reproduce the raw
`/api/chat` call with `format=<schema>` and check the field names in
`message.content` before trusting the generic message.

**Fix pattern**: when a cloud model drifts on field names, add an explicit
field-name contract (required keys + one worked example per drifted section)
to the agent's `*_INSTRUCTIONS` string. This was applied in
`interview_prep_agent.py` and made `gpt-oss:120b-cloud` validate cleanly. Do
**not** weaken the Pydantic schema to match the model — fix the prompt.
Local models like `granite4.1:8b` enforce `json_schema` strictly and rarely
need this.

## PDF-tailoring quirks (resume / cover-letter endpoints)

- `pdflatex` is a **system** binary (MiKTeX/TeX Live), not a pip package. Set
  `LATEX_COMPILER_PATH` in `.env` if it is not on `PATH`.
- **Windows asyncio gotcha**: do not use `asyncio.create_subprocess_exec` for
  `pdflatex`. Run blocking `subprocess` inside `asyncio.to_thread(...)`.
- **Jinja2 gotcha**: never use dict-method names as template context keys
  (e.g. a field named `items`). The resume template uses `(( ... ))` /
  `((* ... *))` delimiters to avoid clashing with LaTeX `{}`. Skill groups use
  the key `skills` for the list of values.
- Tailored PDF/TeX/JSON artifacts are written under `TAILORED_*_DIR` and are
  **not** persisted to Postgres.

## Tests

- `pytest` with `asyncio_mode = "auto"` (`pyproject.toml`) — async test
  functions need no `@pytest.mark.asyncio` to run, though existing tests keep
  it for clarity.
- No `conftest.py` / shared fixtures. API tests build a minimal `FastAPI()`
  app, include only the router under test, and override
  `get_current_user` + `get_<name>_service` via
  `app.dependency_overrides` with `AsyncMock` services. Mirror
  `tests/api/test_skill_gaps.py` / `tests/api/test_interview_prep.py`.
- Agent tests mock `StructuredExtractionClient` with `AsyncMock` and assert
  the pruning/normalization logic (the only real logic in agents).
- Tests do **not** hit Postgres, Ollama, or Chroma — everything is mocked. No
  external services are required to run the suite.

## What is NOT built (do not assume it exists)

Live LinkedIn/Internshala/AICTE scrapers, the Recommendation Agent, the
Application Assistant Agent (the broad cover-letter/interview-prep *orchestrator*
envisioned in SKILL.md §6 — note the individual cover-letter-tailoring and
interview-prep endpoints **are** implemented), the conversations/chatbot API, and
the Streamlit frontend are **not implemented**. The only scraper is
`app/scraper/mocker_scraper.py` (mock data). See SKILL.md §6 for the full
"Done / Not started" breakdown, and ask before expanding scope beyond the
current build target.
