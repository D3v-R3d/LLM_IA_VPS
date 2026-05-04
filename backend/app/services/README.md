# Services

This directory contains business logic and external service integrations.

## Structure

```
services/
├── llm_service.py    # LLM integration service
├── embedding_service.py # Embedding generation service
├── database_service.py # Database operations service
└── README.md         # This file
```

## Service Responsibilities

Each service handles a specific domain:
- **LLM Service**: Interaction with Ollama Cloud API
- **Embedding Service**: Generation and management of embeddings
- **Database Service**: Database operations abstraction

## Design Patterns

Services follow these patterns:
- Single responsibility principle
- Dependency injection for external clients
- Error handling and logging
- Asynchronous operations where appropriate

## Usage

Services are instantiated and used in route handlers:

```python
from app.services.llm_service import LLMService

llm_service = LLMService()
response = await llm_service.generate_text(prompt)
```