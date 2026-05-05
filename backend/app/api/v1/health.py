"""
Health Check API Endpoints Module

This module contains all health check endpoints for monitoring
service availability. Each endpoint verifies a specific service
and returns its operational status.

Endpoints:
- GET /health - General API health
- GET /health/database - PostgreSQL health
- GET /health/qdrant - Qdrant vector database health
- GET /health/ollama - Ollama Cloud API health
"""

from fastapi import APIRouter
from app.services.llm_service import LLMService
from app.services.qdrant_service import QdrantService
from app.services.database_service import DatabaseService
from app.services.telegram_service import TelegramService
from app.core.config import settings


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    General health check endpoint.

    Returns a simple status indicator for load balancers and monitoring systems.

    Returns:
        Dict with overall health status.
    """
    return {"status": "healthy"}


@router.get("/database")
async def health_database():
    """
    PostgreSQL database health check.

    Verifies connectivity to the PostgreSQL database.

    Returns:
        Dict containing status and service name.
    """
    db_service = DatabaseService()
    is_healthy = await db_service.health_check()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "postgresql"
    }


@router.get("/qdrant")
async def health_qdrant():
    """
    Qdrant vector database health check.

    Verifies connectivity to the Qdrant vector database.

    Returns:
        Dict containing status and service name.
    """
    qdrant_service = QdrantService(url=settings.QDRANT_URL)
    is_healthy = qdrant_service.health_check()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "qdrant"
    }


@router.get("/ollama")
async def health_ollama():
    """
    Ollama Cloud API health check.

    Verifies connectivity to the Ollama Cloud API using the configured API key.

    Returns:
        Dict containing status, service name, and API URL.
    """
    llm_service = LLMService(
        base_url=settings.OLLAMA_HOST,
        api_key=settings.OLLAMA_API_KEY
    )
    is_healthy = await llm_service.health_check()
    await llm_service.close()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "ollama",
        "url": settings.OLLAMA_HOST
    }


@router.get("/telegram")
async def health_telegram():
    """
    Telegram bot health check.

    Verifies connectivity to the Telegram Bot API.

    Returns:
        Dict containing status, service name, and bot info.
    """
    telegram_service = TelegramService()
    is_healthy = await telegram_service.health_check()
    bot_info = await telegram_service.get_me()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "telegram",
        "bot_info": bot_info
    }