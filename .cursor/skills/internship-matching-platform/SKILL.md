---
name: internship-matching-platform
description: >-
  Source of truth for the AI-powered internship-matching platform (auth, scraper,
  RAG, multi-agent, Streamlit). Use when generating or editing any code in this
  repository, deciding scope/naming/architecture, or continuing module builds
  (Auth, Job Scraper, RAG, Resume Parser, Agents, Frontend).
---

# SKILL: Internship Matching Platform (AI-Powered)

> This file is the source of truth for what we are building. Read this fully
> before generating or editing any code. When in doubt about scope, naming,
> or architecture, follow what's written here rather than guessing.

## 1. Project Overview

An AI-powered internship-matching platform. Users sign up, upload a resume,
and get matched against ~200 scraped internship listings using a RAG
pipeline + a multi-agent system that also generates tailored resumes, cover
letters, and interview prep.

## 2. Core Modules (functional spec)

### Module 1 — Auth (BUILD THIS FIRST)
- Signup: email, name, password
- Login: validates email + password
- Issues JWT access token + refresh token
- Tokens stored client-side as **HTTP-only cookies**
- Client sends access token with each request
- On access-token expiry, refresh token silently issues a new one
- DB: `users` table (id, email, password hash) + separate `user_profile` table for details
- Stack: JWT + SQLAlchemy ORM (see Module 4, same thing — don't duplicate)

### Module 2 — Job Scraper
- Scrapes internship listings from LinkedIn, Internshala, AICTE (all optional/best-effort — don't hard-fail if one source is blocked)
- Target: ~200 sample jobs per run
- Stores results in `jobs` table

### Module 3 — RAG Ingestion
- Generates embeddings for each scraped job
- Stores embeddings in a vector DB for similarity search against user profile/resume

### Module 4 — Auth internals
- Same as Module 1. JWT creation/validation + SQLAlchemy ORM models live here.

### Module 5 — Resume Parser
- Parses uploaded resume PDF into structured data (skills, education, projects, experience)
- Output feeds the matching + recommendation agents

### Module 6 — Multi-Agent Orchestrator
Five agents coordinated by an orchestrator:

| Agent | Inputs | Tools | Output |
|---|---|---|---|
| Resume Agent | Resume PDF | PDF parser, LLM | Structured profile |
| Job Retrieval Agent | User query + profile | PostgreSQL, vector DB | Relevant internships |
| Recommendation Agent | Profile + retrieved jobs | LLM | Ranked jobs w/ match scores + explanations |
| Application Assistant Agent | Selected job + resume | LLM | Cover letter, resume tweaks, interview questions |
| Interview Prep Agent | Selected job + profile | LLM | Interview guidance |

Also includes a conversational chatbot layer on top of these agents.

### Module 7 — App / Frontend
- Frontend: Streamlit for fast iteration now → migrate to React later if needed
- Talks to the FastAPI backend via the existing API layer

## 3. Directory Structure (target)

```
internship-matching-platform/
│
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPI entry point
│   │
│   ├── api/
│   │   ├── auth.py                     # Signup, login, logout, refresh, /me
│   │   ├── jobs.py                     # List/search scraped jobs
│   │   ├── resumes.py                  # Upload/parse resume
│   │   ├── matching.py                 # Match resume -> jobs
│   │   ├── agents.py                   # Trigger multi-agent workflows
│   │   └── conversations.py            # Chatbot endpoints
│   │
│   ├── auth/
│   │   ├── service.py                  # Signup/login/refresh logic
│   │   ├── jwt.py                      # JWT create/decode/verify
│   │   ├── password.py                 # Password hash/verification
│   │   ├── cookies.py                  # HTTP-only cookie handling
│   │   └── dependencies.py             # get_current_user()
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── job.py
│   │   ├── resume.py
│   │   ├── matching.py
│   │   └── conversation.py
│   │
│   ├── models/                         # SQLAlchemy DB models
│   │   ├── user.py                     # User + UserProfile
│   │   ├── job.py
│   │   ├── resume.py
│   │   ├── conversation.py
│   │   └── message.py
│   │
│   ├── database/
│   │   ├── connection.py               # PostgreSQL connection/session
│   │   ├── base.py                     # SQLAlchemy Base
│   │   └── repositories/
│   │       ├── user_repository.py
│   │       ├── job_repository.py
│   │       ├── resume_repository.py
│   │       └── conversation_repository.py
│   │
│   ├── rag/
│   │   ├── ingestion.py                # Embed + store scraped jobs
│   │   ├── embeddings.py
│   │   ├── vector_store.py             # ChromaDB / pgvector ops
│   │   ├── retriever.py
│   │   ├── chunker.py
│   │   └── config.py
│   │
│   ├── agents/                         # Multi-agent system
│   │   ├── orchestrator.py
│   │   ├── resume_agent.py
│   │   ├── job_retrieval_agent.py
│   │   ├── recommendation_agent.py
│   │   ├── application_assistant_agent.py
│   │   └── interview_prep_agent.py
│   │
│   ├── services/
│   │   ├── resume_service.py
│   │   ├── job_service.py
│   │   ├── matching_service.py
│   │   └── conversation_service.py
│   │
│   ├── scraper/
│   │   ├── linkedin_scraper.py
│   │   ├── internshala_scraper.py
│   │   └── aicte_scraper.py
│   │
│   ├── llm/
│   │   ├── ollama_client.py            # or OpenAI/Anthropic client
│   │   └── prompts/
│   │       ├── recommendation.txt
│   │       ├── cover_letter.txt
│   │       └── interview_prep.txt
│   │
│   ├── core/
│   │   ├── config.py                   # .env/settings
│   │   ├── exceptions.py
│   │   └── logging.py
│   │
│   └── utils/
│       ├── file_utils.py
│       └── helpers.py
│
├── frontend/                            # Streamlit app (for now)
│   └── app.py
│
├── data/
│   └── scraped_jobs/
│
├── uploads/                              # Uploaded resumes
├── vector_db/                            # Local ChromaDB data
├── migrations/                           # Alembic migrations
│
├── tests/
│   ├── test_auth.py
│   ├── test_scraper.py
│   ├── test_ingestion.py
│   ├── test_matching.py
│   └── test_agents.py
│
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── README.md
```

## 4. Tech Stack
- Backend: FastAPI
- ORM: SQLAlchemy
- DB: PostgreSQL (relational) + ChromaDB (vectors)
- Auth: JWT (access + refresh), HTTP-only cookies
- Frontend: Streamlit (v1), React/Vite later if needed
- LLM: pluggable — Ollama local model or hosted API

## 5. Coding Standards

Apply these to every file generated for this project, no exceptions:

- **SOLID principles**
  - *Single Responsibility*: one class/function does one thing (e.g. `jwt.py` only creates/decodes tokens — it doesn't touch the DB or cookies).
  - *Open/Closed*: prefer extension points (interfaces, strategy patterns) over editing existing logic when adding a new scraper source, agent, or LLM provider.
  - *Liskov Substitution*: subclasses/implementations must be swappable without breaking callers (e.g. any `BaseScraper` subclass, any `BaseAgent` subclass).
  - *Interface Segregation*: small, focused interfaces/protocols instead of one giant one (e.g. don't force every repository to implement methods it doesn't need).
  - *Dependency Inversion*: services depend on abstractions (repository interfaces, LLM client protocol), not concrete implementations — inject dependencies rather than instantiating them inline.
- **Type hints everywhere** — every function/method signature (params + return type) is fully typed. No bare `def foo(x):`. Use `Optional`, `list[str]`, `dict[str, Any]`, etc. as appropriate.
- **Dataclasses** for internal, non-API data structures (e.g. parsed resume sections, internal agent state) — use `@dataclass` instead of plain dicts or ad-hoc classes.
- **Pydantic models** for anything crossing an API boundary — all request/response schemas (`app/schemas/*`) and settings/config (`app/core/config.py`) are Pydantic models, not dataclasses or raw dicts.
- **Concise code** — no boilerplate for its own sake, no speculative abstraction for things we don't need yet, no over-commented obvious code. Prefer clear, short functions over long ones; extract only when it genuinely improves readability or reuse.

## 6. Current Build Target

**Auth (Module 1) is implemented.** RAG vector-store foundation (Module 3 partial) is in progress.

Do not build remaining scraper sources, agents, resume parser, or frontend unless asked.
Ask before expanding scope beyond the current target.

### Done — Module 1 (Auth)
1. `app/models/user.py` — User + UserProfile SQLAlchemy models
2. `app/auth/password.py` — hashing/verification
3. `app/auth/jwt.py` — access + refresh token create/decode
4. `app/auth/cookies.py` — set/read HTTP-only cookies
5. `app/auth/service.py` — signup/login/refresh business logic
6. `app/auth/dependencies.py` — `get_current_user()` for protected routes
7. `app/api/auth.py` — `/signup`, `/login`, `/logout`, `/refresh`, `/me` endpoints
8. Supporting: `app/database/connection.py`, `user_repository.py`, `schemas/auth.py`, `core/config.py`, `core/exceptions.py`, `tests/test_auth.py`

### In progress — Module 3 (RAG foundation)
1. `app/rag/config.py` — RAG / Chroma settings (`CHROMA_MODE` http|embedded)
2. `app/rag/embeddings.py` — Ollama embedding service (`mxbai-embed-large`)
3. `app/rag/vector_store.py` — ChromaDB ops (HTTP + embedded modes)
4. `app/rag/ingestion.py` — internship ingestion pipeline
5. `app/rag/retriever.py` — semantic internship retrieval
6. `app/rag/exceptions.py` — RAG domain exceptions
7. `app/schemas/rag.py` — internship / search schemas
8. `app/scraper/mocker_scraper.py` — mock internship data source (not live scrapers yet)
9. `docker-compose.yml` + `docker/chroma-config.yaml` — Chroma server for HTTP mode
10. Tests: `tests/rag/test_config.py`, `tests/rag/test_vector_store.py`

### Not started
- Module 2 live scrapers (LinkedIn / Internshala / AICTE)
- Module 5 Resume Parser
- Module 6 Multi-Agent Orchestrator
- Module 7 Frontend (Streamlit)
- Alembic migrations, jobs API, matching API, agents API, conversations API

## 7. Implemented structure (source of truth for what exists today)

```text
AI Internship Agent/
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPI application entry point
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── auth.py                     # Authentication HTTP endpoints
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── cookies.py                  # HTTP-only authentication cookies
│   │   ├── dependencies.py             # Authentication dependencies
│   │   ├── jwt.py                      # Access and refresh JWT handling
│   │   ├── password.py                 # Password hashing and verification
│   │   └── service.py                  # Authentication business logic
│   │
│   ├── core/
│   │   ├── config.py                   # Environment and application settings
│   │   └── exceptions.py               # Application domain exceptions
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py               # PostgreSQL engine and sessions
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── user_repository.py      # User persistence operations
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py                     # User and user profile models
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── config.py                   # RAG configuration
│   │   ├── embeddings.py               # Ollama embedding service
│   │   ├── exceptions.py               # RAG domain exceptions
│   │   ├── ingestion.py                # Internship ingestion pipeline
│   │   ├── retriever.py                # Semantic internship retrieval
│   │   └── vector_store.py             # ChromaDB vector operations
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                     # Authentication schemas
│   │   └── rag.py                      # Internship and search schemas
│   │
│   └── scraper/
│       └── mocker_scraper.py            # Mock internship data source
│
├── docker/
│   └── chroma-config.yaml              # Chroma server config
│
├── tests/
│   ├── __init__.py
│   ├── test_auth.py                    # Authentication unit tests
│   └── rag/
│       ├── __init__.py
│       ├── test_config.py              # RAG configuration unit tests
│       └── test_vector_store.py        # Chroma client selection unit tests
│
├── vector_db/                          # Local ChromaDB data (embedded mode only)
├── docker-compose.yml                  # Chroma HTTP server
├── .env                                # Local environment variables
├── .env.example                        # Environment variable template
├── .gitignore
├── .python-version
├── pyproject.toml                      # Project metadata and dependencies
├── uv.lock                             # Locked Python dependencies
└── README.md
```

When generating new files, follow the **target** tree in §3. When editing existing code, match patterns already present in §7.
