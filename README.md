# AI Internship Agent

## Implemented project structure

The structure below documents only the files and modules currently implemented in the project.

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
├── tests/
│   ├── __init__.py
│   └── test_auth.py                    # Authentication unit tests
│
├── vector_db/                          # Local ChromaDB data
├── .env                                # Local environment variables
├── .env.example                        # Environment variable template
├── .gitignore
├── .python-version
├── pyproject.toml                      # Project metadata and dependencies
├── uv.lock                             # Locked Python dependencies
└── README.md
```

## Run the application

```powershell
uv sync
uv run python -m uvicorn app.main:app --reload
```

## Run the tests

```powershell
uv run pytest
```
