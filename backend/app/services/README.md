# Services

Business logic organized by domain.

## Structure

```
services/
├── base_service.py           # Base CRUD service
├── context_service.py        # Conversation context/compression
├── conversation_service.py   # Conversation CRUD
├── database_service.py        # PostgreSQL health
├── document_service.py        # Document CRUD
├── message_service.py        # Message CRUD
├── qdrant_service.py         # Qdrant direct access
├── telegram_service.py       # Telegram bot orchestration
├── tools_service.py          # Tools orchestration
├── user_service.py           # User management
│
├── document/                 # Document processing
│   ├── text_extraction.py   # Extract text from formats
│   ├── text_cleaning.py     # Clean/normalise text
│   ├── chunking.py          # Split text into chunks
│   ├── vector_storage.py    # Qdrant operations
│   └── ocr.py               # OCR for images
│
├── llm/                     # LLM interactions
│   ├── llm_base.py          # HTTP client base
│   ├── chat.py               # Chat completions
│   └── embedding.py          # Text embeddings
│
├── tools/                   # External tools
│   ├── web_search.py         # Web search
│   ├── url_fetch.py          # URL content fetch
│   ├── api_caller.py         # HTTP API calls
│   └── tools_service.py      # Unified interface
│
└── telegram/                # Telegram bot
    ├── webhook.py            # Webhook handler
    ├── message_sender.py     # Send messages
    └── command_parser.py     # Parse commands
```

## Services par domaine

### Document (`document/`)

| Service | Responsibility |
|---------|----------------|
| `TextExtractionService` | Extract text from PDF, HTML, TXT, MD |
| `TextCleaningService` | Normalize unicode, remove control chars |
| `ChunkingService` | Split text into overlapping chunks |
| `VectorStorageService` | Store/search vectors in Qdrant |
| `OCRService` | Extract text from images (placeholder) |

### LLM (`llm/`)

| Service | Responsibility |
|---------|----------------|
| `LLMBaseClient` | HTTP client for LLM APIs |
| `ChatService` | Chat completions (Ollama Cloud) |
| `EmbeddingService` | Text embeddings (Ollama local) |

### Tools (`tools/`)

| Service | Responsibility |
|---------|----------------|
| `WebSearchService` | Web search via Ollama Cloud |
| `URLFetchService` | Fetch content from URLs |
| `APICallerService` | Generic HTTP API calls |
| `ToolsService` | Unified interface for LLM tools |

### Telegram (`telegram/`)

| Service | Responsibility |
|---------|----------------|
| `WebhookHandlerService` | Verify and parse webhooks |
| `MessageSenderService` | Send messages to users |
| `CommandParserService` | Parse bot commands |

### Orchestration

| Service | Orchestrates |
|---------|--------------|
| `EmbeddingService` (root) | `document/` + `llm.embedding` + `llm.chat` |
| `TelegramService` (root) | `telegram/` services |
| `ToolsService` (root) | `tools/` services |

## Base Service (`base_service.py`)

Generic CRUD base for database services:

```python
class BaseService(Generic[Model]):
    def get_by_id(db, id) -> Optional[Model]
    def get_all(db, skip, limit) -> List[Model]
    def update(db, id, update_data) -> Optional[Model]
    def delete(db, id) -> bool
```

Used by: `ConversationService`, `MessageService`, `DocumentService`

## Health Checks

| Service | Method |
|---------|--------|
| PostgreSQL | `SELECT 1` |
| Qdrant | `get_collections()` |
| Ollama | `/api/tags` |
| Telegram | `getMe()` |