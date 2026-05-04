# API v1 Endpoints

This directory contains all version 1 API endpoints for the Tower Project.

## Structure

```
api/v1/
├── health.py    - Health check endpoints
└── README.md    - This file
```

## Health Endpoints

All health check endpoints verify service connectivity and return status information.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | General API health status |
| `/health/database` | GET | PostgreSQL database connectivity |
| `/health/qdrant` | GET | Qdrant vector database connectivity |
| `/health/ollama` | GET | Ollama Cloud API connectivity |

## Usage

Import the router in `main.py`:

```python
from app.api.v1.health import router as health_router

app.include_router(health_router)
```

## Response Format

Health endpoints return JSON responses:

```json
{
  "status": "healthy" | "unhealthy",
  "service": "service_name",
  // ... additional service-specific fields
}
```