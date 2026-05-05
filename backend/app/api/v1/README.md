# API v1 Endpoints

This directory contains all version 1 API endpoints for the Tower Project.

## Structure

```
api/v1/
├── chat.py          - Chat completions (Ollama Cloud)
├── ollama.py        - Ollama local health and models
├── embeddings.py    - Document embedding and search
├── documents.py     - Document CRUD operations
├── messages.py      - Message operations
├── conversations.py - Conversation operations
├── users.py         - User management
├── telegram.py      - Telegram bot webhook and notifications
├── health.py        - Health check endpoints
└── README.md        - This file
```

## All Endpoints

### Health (`health.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | General API health status |
| `/health/database` | GET | PostgreSQL database connectivity |
| `/health/qdrant` | GET | Qdrant vector database connectivity |
| `/health/ollama` | GET | Ollama Cloud API connectivity |
| `/health/ollama/test-embed` | GET | Test local Ollama embedding |
| `/health/telegram` | GET | Telegram bot connectivity |

### Chat (`chat.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Generate chat completion (Ollama Cloud) |

### Ollama (`ollama.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ollama/models` | GET | List available Ollama models |
| `/ollama/health` | GET | Check local Ollama health |

### Embeddings (`embeddings.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/embeddings/document` | POST | Embed a single document |
| `/embeddings/documents` | POST | Embed multiple documents |
| `/embeddings/search` | POST | Search similar content |

### Documents (`documents.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/documents` | GET | List all documents |
| `/documents` | POST | Create a document |
| `/documents/{id}` | GET | Get document by ID |
| `/documents/{id}` | PUT | Update document |
| `/documents/{id}` | DELETE | Delete document |
| `/documents/unembedded` | GET | Get unembedded documents |

### Messages (`messages.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/conversations/{id}/messages` | GET | Get messages for conversation |
| `/conversations/{id}/messages` | POST | Create message |

### Conversations (`conversations.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/conversations` | GET | List all conversations |
| `/conversations` | POST | Create conversation |
| `/conversations/{id}` | GET | Get conversation by ID |
| `/conversations/{id}` | DELETE | Delete conversation |

### Users (`users.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users` | GET | List all users |
| `/users` | POST | Create user |
| `/users/{id}` | GET | Get user by ID |
| `/users/{id}` | PUT | Update user |
| `/users/{id}` | DELETE | Delete user |
| `/users/me` | GET | Get current user |

### Telegram (`telegram.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telegram/webhook` | POST | Receive Telegram updates |
| `/telegram/notify/{user_id}` | POST | Send notification to user |
| `/telegram/notify/conversation/{conversation_id}` | POST | Notify all participants |
| `/telegram/setup-webhook` | POST | Set webhook URL |
| `/telegram/webhook` | DELETE | Remove webhook |
| `/telegram/webhook-info` | GET | Get webhook info |
| `/telegram/health` | GET | Bot health check |
| `/telegram/generate-link-token/{user_id}` | GET | Generate link token |

### Bot Commands (via Telegram)

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show help |
| `/status` | Check link status |
| `/register email password name` | Create account and link Telegram |
| `/link email` | Link existing account |
| `/unlink` | Unlink Telegram account |
| `/setpref key=value` | Set a preference (name, language, style, etc.) |
| `/prefs` | Show your preferences |

## Usage

Import routers in `main.py`:

```python
from app.api.v1.chat import router as chat_router
from app.api.v1.ollama import router as ollama_router
from app.api.v1.embeddings import router as embeddings_router
from app.api.v1.documents import router as documents_router
# etc.

app.include_router(chat_router)
app.include_router(ollama_router)
app.include_router(embeddings_router)
app.include_router(documents_router)
# etc.
```

## Response Format

Standard response format:

```json
{
  "status": "success" | "error",
  "data": { ... }
}
```

Error responses:

```json
{
  "status": "error",
  "detail": "Error message"
}
```