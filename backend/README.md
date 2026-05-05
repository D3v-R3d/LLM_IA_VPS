# Backend - FastAPI Application

This directory contains the backend application built with FastAPI for the Tower Project LLM application.

## Structure

```
backend/
├── app/
│   ├── core/           # Core configuration
│   ├── models/         # Database models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic and external services
│   ├── api/v1/         # API endpoints
│   ├── main.py         # Application entry point
├── tests/              # Test suite
├── Dockerfile          # Docker configuration
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Services (`app/services/`)

| Service | Description |
|---------|-------------|
| `llm_service.py` | Ollama API integration (local + cloud) |
| `qdrant_service.py` | Qdrant vector database operations |
| `database_service.py` | PostgreSQL operations |
| `chunking_service.py` | Text chunking for embeddings |
| `embedding_service.py` | Chunk + embed + store pipeline |
| `document_service.py` | Document CRUD operations |
| `context_service.py` | Conversation context management and auto-compression |
| `conversation_service.py` | Conversation and session management |
| `user_service.py` | User preferences and management |
| `telegram_service.py` | Telegram bot operations |
| `tools_service.py` | Tool calling (web search, API calls, URL fetch) |

## Configuration

Context compression settings (in `context_service.py`):
- `max_tokens`: 2000 - Token threshold for auto-compression
- `keep_last_messages`: 15 - Number of recent messages to keep
- `chars_per_token`: 4 - Estimation ratio
- `summary_max_chars`: 4000 - Max text to send to LLM for summarization

Environment variables (set in docker-compose.yml):
- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_URL`: Qdrant server URL
- `OLLAMA_API_BASE`: Ollama Cloud API base URL (https://ollama.com)
- `OLLAMA_API_KEY`: Ollama Cloud API key

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
```

## API Documentation

When running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Dependencies

Main dependencies:
- FastAPI: Web framework
- SQLAlchemy: ORM
- psycopg2-binary: PostgreSQL driver
- Qdrant-client: Vector database client
- httpx: HTTP client
- Pydantic: Data validation