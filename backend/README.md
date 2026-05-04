# Backend - FastAPI Application

This directory contains the backend application built with FastAPI for the Tower Project LLM application.

## Structure

```
backend/
├── app/
│   ├── core/           # Core configuration
│   ├── models/         # Database models
│   ├── services/       # Business logic and external services
│   ├── main.py         # Application entry point
├── tests/              # Test suite
├── Dockerfile          # Docker configuration
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Main Components

- `app/main.py`: Application entry point with health check endpoints
- `app/core/config.py`: Configuration settings for all services
- `app/models/database.py`: SQLAlchemy database setup
- `app/services/`:
  - `llm_service.py`: Ollama Cloud API integration
  - `qdrant_service.py`: Qdrant vector database operations
  - `database_service.py`: PostgreSQL operations

## API Endpoints

### Health Checks
- `GET /health` - Main health check
- `GET /health/database` - PostgreSQL health status
- `GET /health/qdrant` - Qdrant health status
- `GET /health/ollama` - Ollama Cloud health status

## Configuration

Environment variables (set in docker-compose.yml):
- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_URL`: Qdrant server URL
- `OLLAMA_API_BASE`: Ollama Cloud API base URL (https://ollama.com)

## Development

To run the backend locally for development:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload
```

## API Documentation

When running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Dependencies

Main dependencies:
- FastAPI: Web framework
- SQLAlchemy: ORM for database interactions
- psycopg2-binary: PostgreSQL driver
- Qdrant-client: Vector database client
- httpx: HTTP client for Ollama API
- Pydantic: Data validation