# API v1 Endpoints

All endpoints require JWT authentication unless marked as public.

## Structure

```
api/v1/
├── chat.py          # Chat completions (Ollama Cloud)
├── ollama.py        # Ollama local models and testing
├── embeddings.py    # Document embedding and semantic search
├── documents.py     # Document CRUD operations
├── messages.py      # Message operations
├── conversations.py # Conversation CRUD
├── users.py         # User registration and login
├── telegram.py      # Telegram bot webhook
├── health.py        # Health check endpoints
└── README.md
```

## Public Endpoints

These endpoints do NOT require authentication:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/register` | POST | Register new user |
| `/users/login` | POST | Login and get JWT token |
| `/health` | GET | General health status |
| `/health/database` | GET | Database health |
| `/health/qdrant` | GET | Qdrant health |
| `/health/ollama` | GET | Ollama Cloud health |
| `/health/telegram` | GET | Telegram health |

## Protected Endpoints

These require `Authorization: Bearer <token>` header.

### Chat (`/chat`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Generate chat completion |

### Ollama (`/ollama`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ollama/models` | GET | List local Ollama models |
| `/ollama/test-embed` | GET | Test embedding generation |
| `/ollama/chat-models` | GET | List Ollama Cloud models |

### Embeddings (`/embeddings`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/embeddings/document` | POST | Embed a single document |
| `/embeddings/documents` | POST | Embed multiple documents |
| `/embeddings/search` | POST | Semantic search |
| `/embeddings/health` | GET | Embedding service health |

### Documents (`/documents`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/documents` | GET | List user's documents |
| `/documents` | POST | Create document |
| `/documents/{id}` | GET | Get document |
| `/documents/{id}` | PUT | Update document |
| `/documents/{id}` | DELETE | Delete document |
| `/documents/user/{user_id}` | GET | List specific user's documents |

### Messages (`/messages`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/messages` | POST | Create message |
| `/messages/{id}` | GET | Get message |
| `/messages/{id}` | PUT | Update message |
| `/messages/{id}` | DELETE | Delete message |
| `/messages/conversation/{id}` | GET | List conversation messages |

### Conversations (`/conversations`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/conversations` | GET | List user's conversations |
| `/conversations` | POST | Create conversation |
| `/conversations/{id}` | GET | Get conversation |
| `/conversations/{id}` | PUT | Update conversation |
| `/conversations/{id}` | DELETE | Delete conversation |

### Users (`/users`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/me` | GET | Get current user profile |

## Telegram Bot Commands

When linked via Telegram:

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show help |
| `/status` | Check link status |
| `/register email password name` | Create and link account |
| `/link email` | Link existing account |
| `/unlink` | Unlink Telegram |
| `/setpref key=value` | Set preference |
| `/prefs` | Show preferences |

## Telegram Webhook Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telegram/webhook` | POST | Receive Telegram updates |
| `/telegram/webhook` | DELETE | Remove webhook |
| `/telegram/webhook-info` | GET | Get webhook info |
| `/telegram/setup-webhook` | POST | Set webhook URL |
| `/telegram/generate-link-token/{user_id}` | GET | Generate link token |
| `/telegram/notify/{user_id}` | POST | Send notification |
| `/telegram/notify/conversation/{conv_id}` | POST | Notify conversation |