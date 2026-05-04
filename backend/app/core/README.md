# Core Components

This directory contains core application components.

## Structure

```
core/
├── config.py         # Application configuration
└── __init__.py
```

## Configuration

`config.py` handles application configuration using Pydantic Settings:

- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_URL`: Qdrant vector database URL
- `OLLAMA_API_BASE`: Ollama Cloud API base URL

### Environment Variables

Configuration is loaded from environment variables with the following defaults:

```python
DATABASE_URL: str = "postgresql://postgres:password@postgres:5432/tower_db"
QDRANT_URL: str = "http://qdrant:6333"
OLLAMA_API_BASE: str = "https://ollama.com"
```

## Usage

Import settings in other modules:

```python
from app.core.config import settings

# Use settings
database_url = settings.DATABASE_URL
ollama_base = settings.OLLAMA_API_BASE
```