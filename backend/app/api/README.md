# API Routes

This directory contains API route definitions.

## Structure

```
api/
├── v1/               # API version 1
│   ├── api.py        # API router
│   ├── routes/       # Individual route handlers
└── README.md         # This file
```

## Versioning

API routes are versioned to allow for backward compatibility:
- `v1/`: First version of the API

## Route Organization

Routes are organized by resource:
- `chat.py`: Chat-related endpoints
- `documents.py`: Document management endpoints
- `embeddings.py`: Embedding generation and search endpoints

## Implementation

Each route handler:
1. Validates input using Pydantic schemas
2. Calls appropriate service functions
3. Returns properly formatted responses
4. Handles errors appropriately