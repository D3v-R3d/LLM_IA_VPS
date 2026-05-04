# Services

This directory contains business logic and external service integrations.

## Structure

```
services/
├── llm_service.py        # Ollama Cloud integration
├── qdrant_service.py    # Qdrant vector database operations
├── database_service.py  # PostgreSQL operations
└── __init__.py
```

## Service Responsibilities

Each service handles a specific domain:

- **LLM Service**: Interaction with Ollama Cloud API
- **Qdrant Service**: Vector database operations (embeddings storage and search)
- **Database Service**: PostgreSQL database health checks

## LLM Service (`llm_service.py`)

Handles all interactions with Ollama Cloud API:

- `generate()`: Generate text completions via `/api/generate`
- `chat()`: Generate chat completions via `/api/chat`
- `embed()`: Generate embeddings via `/api/embed`
- `list_models()`: List available models via `/api/tags`
- `health_check()`: Verify Ollama Cloud connectivity
- `close()`: Clean up HTTP client

### Usage Example

```python
from app.services.llm_service import LLMService

llm_service = LLMService(base_url="https://ollama.com")
response = await llm_service.generate(
    model="llama3.2",
    prompt="Why is the sky blue?",
    stream=False
)
```

## Qdrant Service (`qdrant_service.py`)

Handles vector database operations:

- `create_collection()`: Create a new collection with specified vector size
- `collection_exists()`: Check if a collection exists
- `insert_vectors()`: Insert vectors with optional payloads
- `search()`: Perform similarity search
- `health_check()`: Verify Qdrant connectivity
- `delete_collection()`: Delete a collection
- `get_collection_info()`: Get collection metadata

### Usage Example

```python
from app.services.qdrant_service import QdrantService

qdrant_service = QdrantService(url="http://qdrant:6333")
results = qdrant_service.search(
    collection_name="my_collection",
    query_vector=[0.1, 0.2, ...],
    limit=5
)
```

## Database Service (`database_service.py`)

Handles PostgreSQL database operations:

- `health_check()`: Verify database connectivity
- `get_version()`: Get PostgreSQL server version

### Usage Example

```python
from app.services.database_service import DatabaseService

db_service = DatabaseService()
is_healthy = await db_service.health_check()
```

## Design Patterns

Services follow these patterns:
- Single responsibility principle
- Dependency injection for external clients
- Error handling and logging
- Asynchronous operations where appropriate

## Health Checks

All services implement `health_check()` method for monitoring:
- PostgreSQL: Executes `SELECT 1` query
- Qdrant: Calls `get_collections()` API
- Ollama: Calls `/api/tags` endpoint