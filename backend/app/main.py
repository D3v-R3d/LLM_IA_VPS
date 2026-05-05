"""
FastAPI Main Application Module

This module initializes and configures the FastAPI application for the Tower Project.
It sets up middleware, service clients, and health check endpoints.

The application uses:
- CORS middleware for cross-origin requests from the frontend
- LLM service for Ollama Cloud API integration
- Qdrant service for vector similarity search
- Database service for PostgreSQL operations

Health check endpoints are provided for monitoring service availability.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.services.llm_service import LLMService
from app.api.v1.health import router as health_router
from app.api.v1.users import router as users_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.messages import router as messages_router
from app.api.v1.documents import router as documents_router
from app.api.v1.embeddings import router as embeddings_router
from app.api.v1.ollama import router as ollama_router
from app.api.v1.chat import router as chat_router
from app.api.v1.telegram import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Handles resource allocation when the application starts and
    cleanup when it shuts down.

    On shutdown:
    - Closes the LLM service HTTP client to release connections
    """
    yield
    # Cleanup: Close the async HTTP client used by LLMService
    # Import here to avoid circular imports
    from app.services.llm_service import LLMService
    llm_service = LLMService(base_url=settings.OLLAMA_HOST)
    await llm_service.close()


app = FastAPI(
    title="Tower Project API",
    description="API for the Tower Project LLM application",
    version="1.0.0"
)


# CORS middleware allows the frontend to make requests to this API
# The frontend runs on a different origin (domain/port) than the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # Allow all origins (configure for production)
    allow_credentials=True,           # Allow cookies and auth headers
    allow_methods=["*"],              # Allow all HTTP methods
    allow_headers=["*"],              # Allow all HTTP headers
)


# Include health check routers from API v1
# These endpoints verify connectivity to backend services
app.include_router(health_router)
app.include_router(users_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(embeddings_router, prefix="/api/v1")
app.include_router(ollama_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(telegram_router, prefix="/api/v1")


@app.get("/")
def read_root():
    """
    Root endpoint returning a welcome message.

    Returns:
        Dict with a welcome message for API consumers.
    """
    return {"message": "Welcome to the Tower Project API"}


if __name__ == "__main__":
    """
    Development server runner.

    When running directly with `python main.py`, this starts the
    FastAPI application using Uvicorn ASGI server on port 8000.

    For production, use Gunicorn or another ASGI server with
    workers for better performance and reliability.
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)