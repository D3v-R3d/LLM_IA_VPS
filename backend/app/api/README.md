# API Routes

This directory contains API route definitions organized by version.

## Structure

```
api/
├── v1/               # API version 1
│   ├── chat.py       # Chat completions
│   ├── ollama.py     # Ollama health and models
│   ├── embeddings.py # Document embedding and search
│   ├── documents.py  # Document CRUD
│   ├── messages.py   # Message operations
│   ├── conversations.py # Conversation CRUD
│   ├── users.py      # User management
│   ├── telegram.py   # Telegram bot webhook
│   ├── health.py     # Health check endpoints
│   └── README.md
├── __init__.py
└── README.md
```

## Health Check Endpoints (`/health`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | General API health |
| `/health/database` | GET | PostgreSQL connectivity |
| `/health/qdrant` | GET | Qdrant vector DB connectivity |
| `/health/ollama` | GET | Ollama Cloud API connectivity |
| `/health/telegram` | GET | Telegram bot connectivity |

## Route Organization

Routes are organized by resource:
- **chat.py**: Chat completions (Ollama Cloud)
- **documents.py**: Document management
- **embeddings.py**: Embedding generation and search
- **messages.py**: Message CRUD
- **conversations.py**: Conversation CRUD
- **users.py**: User registration, login, profile
- **telegram.py**: Telegram bot webhook handler
- **ollama.py**: Ollama local server health and models

## Authentication

All endpoints except `/users/register`, `/users/login`, and `/health/*` require JWT authentication:

```
Authorization: Bearer <token>
```

## Rate Limiting

- `/chat` endpoint: 30 requests per minute

## Error Responses

```json
{
  "detail": "Error message"
}
```

Standard HTTP status codes: 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found), 422 (Validation Error), 429 (Rate Limited)