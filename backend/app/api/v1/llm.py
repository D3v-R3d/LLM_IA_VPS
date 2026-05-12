"""
LLM Providers API

Endpoints for managing LLM providers (Ollama, Groq, etc.)
"""

from fastapi import APIRouter, HTTPException
from app.providers.llm.provider_factory import provider_factory

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/models")
async def list_provider_models(provider: str = None):
    """
    List available models from LLM providers.
    
    - If provider specified, list models for that provider
    - If no provider, list models for current default provider
    """
    try:
        if provider:
            p = provider_factory.get_provider(provider)
        else:
            p = provider_factory.get_provider()
        models = await p.list_models()
        return {
            "status": "healthy",
            "provider": p.name,
            "models": models
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Provider error: {str(e)}")


@router.get("/providers")
async def list_providers():
    """List available LLM providers."""
    return {
        "providers": provider_factory.list_providers(),
        "default": provider_factory.get_default_provider_name()
    }


@router.get("/health")
async def check_provider_health(provider: str = None):
    """Check health of LLM provider(s)."""
    try:
        if provider:
            p = provider_factory.get_provider(provider)
            healthy = await p.health_check()
            return {"provider": p.name, "healthy": healthy}
        else:
            results = {}
            for name in provider_factory.list_providers():
                try:
                    p = provider_factory.get_provider(name)
                    results[name] = await p.health_check()
                except Exception:
                    results[name] = False
            return {"providers": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))