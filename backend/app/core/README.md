# Core Components

This directory contains core application components for configuration, authentication, and rate limiting.

## Structure

```
core/
├── config.py         # Application configuration (Pydantic Settings)
├── auth.py           # JWT authentication service and dependencies
├── rate_limit.py     # Rate limiting configuration (slowapi)
├── __init__.py
└── README.md
```

## Configuration (`config.py`)

Loads settings from environment variables using Pydantic Settings.

**Environment Variables:**
- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_URL`: Qdrant vector database URL
- `OLLAMA_HOST`: Ollama local server URL
- `OLLAMA_CLOUD_HOST`: Ollama Cloud API URL
- `OLLAMA_API_KEY`: Ollama Cloud API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_SECRET_TOKEN`: Telegram webhook secret
- `JWT_SECRET`: Secret key for JWT tokens

## Authentication (`auth.py`)

JWT-based authentication for API endpoints.

**Key Components:**
- `AuthService`: Static methods for password hashing, token creation/decoding
- `get_current_user`: FastAPI dependency for protected endpoints
- `get_current_user_optional`: FastAPI dependency for optional auth

**Token Configuration:**
- Algorithm: HS256
- Expiration: 7 days

## Rate Limiting (`rate_limit.py`)

API rate limiting using slowapi.

**Limits:**
- Default: 30 requests per minute on `/chat` endpoint

## Usage

```python
from app.core.config import settings, get_settings
from app.core.auth import get_current_user
from app.core.rate_limit import limiter

# Access settings
db_url = settings.DATABASE_URL

# Protect endpoints
@router.post("/protected")
def protected_endpoint(current_user_id: UUID = Depends(get_current_user)):
    ...

# Apply rate limiting
@router.post("/chat")
@limiter.limit("30/minute")
async def chat(...):
    ...
```