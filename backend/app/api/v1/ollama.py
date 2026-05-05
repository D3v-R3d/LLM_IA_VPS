from fastapi import APIRouter, HTTPException
from app.services.llm_service import LLMService
from app.core.config import settings


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ollama")
async def health_ollama():
    llm_service = LLMService(base_url=settings.OLLAMA_HOST)
    is_healthy = await llm_service.health_check()
    await llm_service.close()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "ollama",
        "url": settings.OLLAMA_HOST
    }


@router.get("/ollama/models")
async def list_ollama_models():
    llm_service = LLMService(base_url=settings.OLLAMA_HOST)
    try:
        result = await llm_service.list_models()
        await llm_service.close()
        return {
            "status": "healthy",
            "service": "ollama",
            "url": settings.OLLAMA_HOST,
            "models": result.get("models", [])
        }
    except Exception as e:
        await llm_service.close()
        raise HTTPException(status_code=503, detail=f"Ollama API error: {str(e)}")


@router.get("/ollama/test-embed")
async def test_embedding():
    llm_service = LLMService(base_url=settings.OLLAMA_HOST)
    try:
        result = await llm_service.embed(
            model="nomic-embed-text",
            input="This is a test sentence."
        )
        await llm_service.close()
        embeddings = result.get("embeddings", [])
        return {
            "status": "healthy",
            "service": "ollama",
            "embedding_model": "nomic-embed-text",
            "embedding_dimensions": len(embeddings[0]) if embeddings else 0,
            "embeddings_count": len(embeddings)
        }
    except Exception as e:
        await llm_service.close()
        raise HTTPException(status_code=503, detail=f"Embedding error: {str(e)}")


@router.get("/ollama/chat-models")
async def list_chat_models():
    llm_service = LLMService(base_url=settings.OLLAMA_CLOUD_HOST, api_key=settings.OLLAMA_API_KEY)
    try:
        result = await llm_service.list_models()
        await llm_service.close()
        return {
            "status": "healthy",
            "service": "ollama-cloud",
            "url": settings.OLLAMA_CLOUD_HOST,
            "models": result.get("models", [])
        }
    except Exception as e:
        await llm_service.close()
        raise HTTPException(status_code=503, detail=f"Ollama Cloud API error: {str(e)}")