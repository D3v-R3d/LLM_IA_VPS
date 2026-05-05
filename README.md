# Tower Project - LLM Application

This project implements a full-stack RAG application with Telegram bot integration.

## Architecture

```
tower_project/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/v1/      # API endpoints
│   │   ├── core/        # Configuration
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── main.py
│   └── tests/
├── frontend/             # React frontend
├── docker/               # Docker configs
└── docker-compose.yml
```

## Services

| Service | Description |
|---------|-------------|
| PostgreSQL | Structured data (users, conversations, messages, documents) |
| Qdrant | Vector storage for embeddings |
| Ollama Cloud | Chat completions (minimax-m2.7) |
| Local Ollama | Embeddings (nomic-embed-text, 768 dims) |
| Telegram Bot | Bidirectional messaging with users |
| Traefik | Reverse proxy with SSL |

## API Endpoints

### Health
- `GET /health` - Overall health
- `GET /health/database` - PostgreSQL
- `GET /health/qdrant` - Qdrant
- `GET /health/ollama` - Ollama Cloud
- `GET /health/telegram` - Telegram bot

### Chat
- `POST /chat` - Chat completion (Ollama Cloud)

### Embeddings
- `POST /embeddings/document` - Embed single document
- `POST /embeddings/documents` - Embed multiple documents
- `POST /embeddings/search` - Semantic search

### Telegram
- `POST /telegram/webhook` - Receive Telegram updates
- `POST /telegram/notify/{user_id}` - Send notification

## Getting Started

```bash
# Start all services
docker-compose up -d --build

# Check health
curl http://localhost:8000/health
```

## Telegram Bot

The Telegram bot (`@R3d0n3_Bot`) provides bidirectional messaging with session support and auto-compression.

### Commands
- `/register email password name` - Create account and link Telegram
- `/link email` - Link existing account
- `/unlink` - Unlink Telegram account
- `/status` - Check link status
- `/help` - Show help
- `/new` - Start a new session (conversation)
- `/sessions` - List all your sessions
- `/reset` - Reset current session
- `/compress` - Manually compress conversation history
- `/setpref key=value` - Set user preference
- `/prefs` - Show current preferences

### Session Management
Sessions keep conversations isolated. Use `/new` to start fresh, `/sessions` to switch between sessions.

### Auto-Compression
When conversation exceeds 2000 tokens, the bot automatically compresses history by:
1. Summarizing old messages via LLM
2. Keeping last 15 messages
3. Prepending summary as context

This prevents token overflow while preserving important context.

### Web Access Tools
The bot can access the internet on demand:
- **Search**: `search_web(query)` - DuckDuckGo search
- **Fetch**: `fetch_url(url)` - Read webpage content
- **API**: `call_api(url, method, headers, body)` - Call external APIs

Example: "What's the weather in Tokyo?" → Bot searches web → Returns result

## RAG Flow

1. **Document → Chunks** (chunking_service.py)
2. **Chunks → Embeddings** (local Ollama nomic-embed-text)
3. **Embeddings → Qdrant** (qdrant_service.py)
4. **Query → Similarity Search** (embedding_service.py search_similar)
5. **Context + Query → LLM** (Ollama Cloud)

## Deployment

- Frontend: https://www.srv1632761.hstgr.cloud
- Backend API: https://api.srv1632761.hstgr.cloud/api
- Qdrant Dashboard: https://api.srv1632761.hstgr.cloud/qdrant

Traefik handles SSL termination with Let's Encrypt certificates.