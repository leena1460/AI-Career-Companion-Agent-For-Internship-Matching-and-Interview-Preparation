# AI Internship Agent

AI-powered internship matching platform. Users sign up, upload a resume, and get
matched against scraped internship listings using a RAG pipeline. They can also
tailor a resume toward a job and download a PDF.

## Implemented project structure

```text
AI Internship Agent/
├── app/
│   ├── main.py                         # FastAPI entry point
│   ├── api/
│   │   ├── auth.py                     # Signup, login, logout, refresh, /me
│   │   ├── jobs.py                     # Authenticated scrape + list jobs
│   │   ├── matching.py                 # Authenticated internship matching
│   │   ├── resume_tailoring.py         # Authenticated resume → PDF tailoring
│   │   └── user_details.py             # Resume / cover letter / profile summary
│   ├── auth/                           # JWT, cookies, password, dependencies
│   ├── agents/                         # Matching + resume-tailoring agents
│   ├── services/
│   │   ├── job_scrape_service.py       # Parallel Postgres + RAG persist
│   │   ├── profile_service.py
│   │   ├── resume_tailoring_service.py # LLM → Jinja LaTeX → pdflatex
│   │   └── user_detail_service.py
│   ├── templates/resume/
│   │   └── resume_template.tex.j2      # Jinja LaTeX resume template
│   ├── database/
│   │   ├── connection.py
│   │   └── repositories/
│   ├── models/                         # User, UserDetail, Job
│   ├── rag/                            # Embeddings, Chroma, ingestion, retrieval
│   ├── schemas/
│   ├── scraper/
│   │   └── mocker_scraper.py           # Mock internship data source
│   ├── llm/
│   └── utils/
│       ├── file_utils.py
│       └── latex_utils.py              # escape_latex / sanitize_url
├── tailored_resumes/                   # Generated JSON/TeX/PDF artifacts
├── migrations/
│   └── versions/
│       ├── 20260730_0001_initial_schema.py
│       ├── 20260805_0002_create_jobs_table.py
│       └── 20260808_0003_add_resume_linkedin.py
├── tests/
├── docker-compose.yml                  # Chroma HTTP server
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Authentication policy

JWT access and refresh tokens are stored in **HTTP-only cookies**.

| Kind | Endpoints |
| --- | --- |
| Public | `GET /health`, `POST /auth/signup`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `/docs` |
| Protected | every other business endpoint (requires a valid access-token cookie) |

New endpoints must use `get_current_user` (router-level dependency preferred).
Clients do **not** send a `user_id`; ownership comes from the verified cookie.

## API overview

### Auth

| Method | Path | Auth |
| --- | --- | --- |
| `POST` | `/auth/signup` | No |
| `POST` | `/auth/login` | No |
| `POST` | `/auth/refresh` | Refresh cookie |
| `POST` | `/auth/logout` | No |
| `GET` | `/auth/me` | Access cookie |

### Jobs (scrape + list)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `POST` | `/jobs/scrape?reset_vectors=true` | Required | Runs mock scraper, then concurrently writes to Postgres `jobs` and RAG/Chroma |
| `GET` | `/jobs` | Required | Lists jobs from PostgreSQL |

Each scrape **replaces** existing Postgres rows and (by default) resets the Chroma collection before re-indexing.

### User documents

| Method | Path | Auth |
| --- | --- | --- |
| `POST` | `/resumes/parse` | Required |
| `GET` | `/resumes` | Required |
| `POST` | `/cover-letters/parse` | Required |
| `GET` | `/cover-letters` | Required |
| `POST` | `/profile-summary` | Required |

### Matching

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `POST` | `/matching` | Required | Multipart: either `user_detail_id` **or** a new PDF/DOCX `file`, not both |

Skills used for matching = signup profile skills **merged with** resume skills.

### Resume tailoring

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `POST` | `/resume-tailoring` | Required | Multipart: `instructions` + exactly one of `file` or `user_detail_id`; optional `job_id`. Returns PDF |

Flow: JWT auth → load user/profile → parse or load resume → optional job → Ollama structured JSON → Jinja LaTeX → `pdflatex` → `FileResponse`. Tailored artifacts are written under `TAILORED_RESUME_DIR/<user_id>/<resume_id>/` (not stored in Postgres).

Requires a local TeX install (see [LaTeX (resume PDF)](#latex-resume-pdf) below).

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Setup

```powershell
uv sync
copy .env.example .env
```

Edit `.env` with your PostgreSQL password and secrets.

### PostgreSQL

Start the local Postgres service, then apply migrations:

```powershell
uv run alembic upgrade head
```

If the database was created earlier via app startup `create_all`, mark the baseline as applied:

```powershell
uv run alembic stamp head
```

### ChromaDB (vector store)

| Mode | Storage | Notes |
| --- | --- | --- |
| `http` (default) | Standalone Chroma server | Preferred for browsing with a GUI |
| `embedded` | Local `vector_db/` | No external server |

```powershell
docker compose up -d
curl http://localhost:6333/api/v2/heartbeat
```

```ini
CHROMA_MODE=http
CHROMA_HOST=localhost
CHROMA_PORT=6333
```

### Ollama

```powershell
ollama pull mxbai-embed-large
ollama pull granite4.1:8b
```

### LaTeX (resume PDF)

`POST /resume-tailoring` renders a Jinja2 `.tex` template and compiles it with **`pdflatex`**. Jinja2 is installed via `uv sync`; `pdflatex` is a system TeX tool (not a pip package).

Install one of:

| Option | Platform | Install |
| --- | --- | --- |
| **MiKTeX** (recommended on Windows) | Windows | `winget install MiKTeX.MiKTeX` |
| **TeX Live** | Windows / macOS / Linux | [tug.org/texlive](https://tug.org/texlive/) |

After install, either ensure `pdflatex` is on your `PATH`, or set the full binary path in `.env`:

```ini
LATEX_COMPILER_PATH=pdflatex
# Windows MiKTeX example:
# LATEX_COMPILER_PATH=C:\Users\<you>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe
LATEX_COMPILE_TIMEOUT_SECONDS=60
RESUME_TEMPLATE_PATH=app/templates/resume/resume_template.tex.j2
TAILORED_RESUME_DIR=tailored_resumes
```

On first compile, MiKTeX may prompt to install missing packages — allow automatic install (`initexmf --set-config-value=[MPM]AutoInstall=1` if needed).

Optional one-off RAG ingestion (also covered by `POST /jobs/scrape`):

```powershell
uv run python -m app.rag.ingestion
```

## Run the application

```powershell
uv run python -m uvicorn app.main:app --reload
```

Typical flow in `/docs`:

1. `POST /auth/signup` or `POST /auth/login` (cookies are set automatically)
2. `POST /jobs/scrape` to load jobs into Postgres + Chroma
3. `GET /jobs` to inspect stored jobs
4. Upload a resume / run `POST /matching`
5. `POST /resume-tailoring` with instructions + resume/`user_detail_id` (+ optional `job_id`) to download a tailored PDF

## Run the tests

```powershell
uv run pytest
```
