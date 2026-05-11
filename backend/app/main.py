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

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import asyncio

from app.core.config import settings
from app.core.rate_limit import limiter
from app.api.v1.health import router as health_router
from app.api.v1.users import router as users_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.messages import router as messages_router
from app.api.v1.documents import router as documents_router
from app.api.v1.embeddings import router as embeddings_router
from app.api.v1.ollama import router as ollama_router
from app.api.v1.llm import router as llm_router
from app.api.v1.chat import router as chat_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.user_model_prefs import router as user_model_prefs_router
from app.api.v1.tools import router as tools_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Handles resource allocation when the application starts and
    cleanup when it shuts down.
    """
    from app.core.lock_manager import get_lock_manager

    lock_manager = get_lock_manager()
    await lock_manager.start_cleanup_task()

    yield

    await lock_manager.stop()


app = FastAPI(
    title="Tower Project API",
    description="API for the Tower Project LLM application",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# CORS middleware allows the frontend to make requests to this API
allowed_origins = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "https://www.srv1632761.hstgr.cloud,https://api.srv1632761.hstgr.cloud"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Include routers
app.include_router(health_router)
app.include_router(users_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(embeddings_router, prefix="/api/v1")
app.include_router(ollama_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(telegram_router, prefix="/api/v1")
app.include_router(user_model_prefs_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")


@app.get("/")
def read_root():
    """Root endpoint returning a welcome message."""
    return {"message": "Welcome to the Tower Project API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)