from fastapi import APIRouter, HTTPException
from app.services.llm import ChatService as LLMService, EmbeddingService
from app.core.config import settings


router = APIRouter(prefix="/ollama", tags=["ollama"])


@router.get("/models")
async def list_ollama_models():
    embedding_service = EmbeddingService(base_url=settings.OLLAMA_HOST)
    try:
        models = await embedding_service.list_models()
        await embedding_service.close()
        return {
            "status": "healthy",
            "service": "ollama",
            "url": settings.OLLAMA_HOST,
            "models": models
        }
    except Exception as e:
        await embedding_service.close()
        raise HTTPException(status_code=503, detail=f"Ollama API error: {str(e)}")


@router.get("/test-embed")
async def test_embedding():
    embedding_service = EmbeddingService(base_url=settings.OLLAMA_HOST)
    try:
        result = await embedding_service.embed("This is a test sentence.")
        await embedding_service.close()
        embeddings = result.get("embeddings", [])
        return {
            "status": "healthy",
            "service": "ollama",
            "embedding_model": "nomic-embed-text",
            "embedding_dimensions": len(embeddings[0]) if embeddings else 0,
            "embeddings_count": len(embeddings)
        }
    except Exception as e:
        await embedding_service.close()
        raise HTTPException(status_code=503, detail=f"Embedding error: {str(e)}")


@router.get("/chat-models")
async def list_chat_models():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{settings.OLLAMA_CLOUD_HOST}/api/tags",
                headers={"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"}
            )
            result = response.json()
            return {
                "status": "healthy",
                "service": "ollama-cloud",
                "url": settings.OLLAMA_CLOUD_HOST,
                "models": result.get("models", [])
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama Cloud API error: {str(e)}")