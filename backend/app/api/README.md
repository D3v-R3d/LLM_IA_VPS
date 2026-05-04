# API Routes

This directory contains API route definitions.

## Structure

```
api/
├── v1/               # API version 1
│   ├── api.py        # API router
│   ├── routes/       # Individual route handlers
│   └── README.md
└── README.md
```

## Health Check Endpoints

The main application (`app/main.py`) provides the following health check endpoints:

### Main Health Check
```
GET /health
```
Returns overall application health status.

### Service Health Checks
```
GET /health/database
GET /health/qdrant
GET /health/ollama
```
Returns health status for each external service:
- `database`: PostgreSQL database
- `qdrant`: Qdrant vector database
- `ollama`: Ollama Cloud API

### Response Format

```json
{
  "status": "healthy" | "unhealthy",
  "service": "service_name"
}
```

## Route Organization

Routes are organized by resource (when implemented):
- `chat.py`: Chat-related endpoints
- `documents.py`: Document management endpoints
- `embeddings.py`: Embedding generation and search endpoints

## Implementation

Each route handler:
1. Validates input using Pydantic schemas
2. Calls appropriate service functions
3. Returns properly formatted responses
4. Handles errors appropriately

## API Versioning

API routes are versioned to allow for backward compatibility:
- `v1/`: First version of the API