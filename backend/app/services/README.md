# Services

This directory contains business logic and external service integrations.

## Structure

```
services/
├── chunking_service.py    # Text chunking for embeddings
├── embedding_service.py    # Embedding generation and storage
├── llm_service.py          # Ollama API (local + cloud)
├── qdrant_service.py       # Qdrant vector database operations
├── database_service.py     # PostgreSQL operations
├── telegram_service.py     # Telegram bot API
├── tools_service.py        # Web search, URL fetch, API calls
├── document_service.py     # Document CRUD
└── __init__.py
```

## Service Responsibilities

Each service handles a specific domain:

- **LLM Service**: Interaction with Ollama API (local for embeddings, cloud for chat)
- **Qdrant Service**: Vector database operations (embeddings storage and search)
- **Chunking Service**: Text splitting for embedding
- **Embedding Service**: Orchestrates chunking + embedding + storage
- **Database Service**: PostgreSQL database health checks

## LLM Service (`llm_service.py`)

Handles all interactions with Ollama API:

- `generate()`: Generate text completions via `/api/generate`
- `chat()`: Generate chat completions via `/api/chat` (uses cloud API)
- `embed()`: Generate embeddings via `/api/embed` (uses local API)
- `list_models()`: List available models via `/api/tags`
- `health_check()`: Verify Ollama connectivity
- `close()`: Clean up HTTP client

### Usage Example

```python
from app.services.llm_service import LLMService

# Local (embeddings)
llm_service = LLMService(base_url="http://ollama:11434")
embeddings = await llm_service.embed(model="nomic-embed-text", input="text")

# Cloud (chat)
llm_service = LLMService(base_url="https://ollama.com", api_key="key")
response = await llm_service.chat(model="gemma4:31b", messages=[{"role": "user", "content": "Hi"}])
```

## Qdrant Service (`qdrant_service.py`)

Handles vector database operations:

### Collections
- `create_collection()`: Create a new collection with specified vector size
- `collection_exists()`: Check if a collection exists
- `get_collection_info()`: Get collection metadata
- `delete_collection()`: Delete a collection

### Points (CRUD)
- `insert_vectors()`: Insert vectors with optional payloads
- `get_point()`: Retrieve a single point by ID
- `delete()`: Delete points by ID
- `scroll_points()`: Paginate through points
- `count_points()`: Count points in collection
- `update_vectors()`: Update vectors
- `delete_vectors()`: Delete vectors
- `set_payload()`: Set payload fields
- `delete_payload()`: Delete payload fields

### Search
- `search()`: Perform similarity search
- `search_batch()`: Search with multiple query vectors
- `recommend()`: "More like this" recommendation

### Indexing
- `create_payload_index()`: Create index on payload field for faster filtering

### Usage Example

```python
from app.services.qdrant_service import QdrantService

qdrant = QdrantService(url="http://qdrant:6333")

# Create collection
qdrant.create_collection("documents", vector_size=768)

# Insert vectors
qdrant.insert_vectors("documents", [[0.1, 0.2, ...]], [{"text": "sample"}])

# Search
results = qdrant.search("documents", query_vector=[0.1, 0.2, ...], limit=5)

# Scroll (pagination)
result = qdrant.scroll_points("documents", limit=100)
while result["points"]:
    for point in result["points"]:
        print(f"ID: {point['id']}")
    if result["next_page_offset"]:
        result = qdrant.scroll_points("documents", offset=result["next_page_offset"])
    else:
        break

# Count
count = qdrant.count_points("documents")

# Recommend
results = qdrant.recommend("documents", positive_ids=["point-id"], limit=5)

# Index
qdrant.create_payload_index("documents", "document_id")
```

## Chunking Service (`chunking_service.py`)

Splits text into chunks for embedding:

- `chunk_text()`: Split text into overlapping chunks
- `chunk_documents()`: Chunk multiple documents

### Usage Example

```python
from app.services.chunking_service import ChunkingService

service = ChunkingService(chunk_size=500, chunk_overlap=50)
chunks = service.chunk_text("Long document text...")
```

## Embedding Service (`embedding_service.py`)

Orchestrates the full embedding pipeline:

- `embed_document()`: Chunk + embed + store in Qdrant
- `embed_documents()`: Process multiple documents
- `search_similar()`: Find similar chunks by text query
- `health_check()`: Check all services

### Usage Example

```python
from app.services.embedding_service import EmbeddingService

service = EmbeddingService()

# Embed a document
result = await service.embed_document({
    "id": "doc-1",
    "name": "Document",
    "content_raw": "Text content..."
})

# Search
results = await service.search_similar("query text", limit=5)
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

## Telegram Service (`telegram_service.py`)

Handles Telegram Bot API operations:

- `send_message()`: Send text message to user
- `send_photo()`: Send photo to user
- `send_document()`: Send document to user
- `send_notification()`: Send formatted notification
- `set_webhook()`: Configure webhook URL
- `verify_webhook()`: Verify webhook requests
- `health_check()`: Verify bot connectivity
- `parse_command()`: Parse commands from text

### Usage Example

```python
from app.services.telegram_service import TelegramService

telegram = TelegramService()

# Send message
await telegram.send_message(chat_id="123456789", text="Hello!")

# Send typing indicator
await telegram.send_chat_action(chat_id="123456789", action="typing")

# Send notification
await telegram.send_notification(
    chat_id="123456789",
    title="New Message",
    message="You have a new message",
    notification_type="info"
)

# Set webhook
await telegram.set_webhook("https://yourdomain.com/api/v1/telegram/webhook")
```

### Bot Commands

Users can interact with the bot via Telegram:
- `/start` - Welcome message
- `/help` - Show help
- `/status` - Check link status
- `/register email password name` - Create account and link Telegram
- `/link email` - Link existing account to Telegram
- `/unlink` - Unlink Telegram account
- `/setpref key=value` - Set user preference (name, language, style, timezone, etc.)
- `/prefs` - View your preferences
- Any other text - Sent to LLM (minimax-m2.7) with tool access, response returned via bot

### User Preferences

Users can store preferences via `/setpref`:
```
/setpref name=John
/setpref language=fr
/setpref style=concise
/setpref timezone=Europe/Paris
```

Preferences are injected into the LLM system prompt so the bot remembers user settings.

## Tools Service (`tools_service.py`)

Provides tools for LLM to interact with external services:

- `search_web()` - Search the web via DuckDuckGo
- `fetch_url()` - Fetch content from a URL
- `call_api()` - Call external APIs
- `execute_tool()` - Execute a tool by name

Used by LLM for real-time information access.

```python
from app.services.tools_service import ToolsService

tools = ToolsService()
results = await tools.search_web("weather in Paris", num_results=3)
content = await tools.fetch_url("https://news.example.com")
api_result = await tools.call_api("https://api.example.com/data", method="GET")
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
- Telegram: Calls `getMe` API