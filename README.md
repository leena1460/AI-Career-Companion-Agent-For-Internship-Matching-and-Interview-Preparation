# AI Internship Agent

## **Implemented project structure**

**The structure below documents only the files and modules currently implemented in the project.**

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
├── tests/
│   ├── __init__.py
│   ├── test_auth.py                    # Authentication unit tests
│   └── rag/
│       ├── __init__.py
│       ├── test_config.py              # RAG configuration unit tests
│       └── test_vector_store.py        # Chroma client selection unit tests
│
├── vector_db/                          # Local ChromaDB data (embedded mode only)
├── .env                                # Local environment variables
├── .env.example                        # Environment variable template
├── .gitignore
├── .python-version
├── pyproject.toml                      # Project metadata and dependencies
├── uv.lock                             # Locked Python dependencies
└── README.md
```



## Vector store

The RAG layer talks to ChromaDB in one of two modes, selected by `CHROMA_MODE`.


| Mode             | Storage                      | Visible in the Chroma DB VS Code extension |
| ---------------- | ---------------------------- | ------------------------------------------ |
| `http` (default) | Standalone Chroma server     | Yes                                        |
| `embedded`       | Local `vector_db/` directory | No                                         |


Use `http` when you want to browse the data with a GUI client. Start the server first:

```powershell
docker run --rm -p 6333:8000 chromadb/chroma:latest
curl http://localhost:6333/api/v2/heartbeat
```

Relevant environment variables:

```ini
CHROMA_MODE=http
CHROMA_HOST=localhost
CHROMA_PORT=6333
```



## RAG module

Ollama must be running with the `mxbai-embed-large` model pulled.

### Ingestion

```powershell
ollama pull mxbai-embed-large
uv run python -m app.rag.ingestion
```



### Sample retrieval

```powershell
uv run python -c "from app.rag.retriever import InternshipRetriever; results = InternshipRetriever().search('Python ML internship in Bangalore'); print(results)"
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

