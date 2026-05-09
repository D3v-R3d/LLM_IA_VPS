from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.services.llm import ChatService as LLMService
from app.core.config import settings
from app.core.rate_limit import limiter
from fastapi import Request

import os

router = APIRouter(prefix="/chat", tags=["chat"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    stream: bool = False
    options: Optional[dict] = None
    provider: Optional[str] = None


class ChatResponse(BaseModel):
    model: str
    message: dict
    done: bool


@router.post("", response_model=ChatResponse)
@limiter.limit(os.environ.get("CHAT_RATE_LIMIT", "30/minute"))
async def chat(request: Request, chat_request: ChatRequest):
    from app.services.llm.provider_factory import provider_factory

    provider_name = chat_request.provider or settings.LLM_PROVIDER
    provider = provider_factory.get_provider(provider_name)

    try:
        model = chat_request.model
        if not model:
            models = await provider.list_models()
            if models:
                first = models[0]
                model = first.get("id") or first.get("name") or first.get("model", "")
        
        if not model:
            raise HTTPException(status_code=400, detail="No model available")

        messages = [{"role": m.role, "content": m.content} for m in chat_request.messages]
        result = await provider.chat(
            model=model,
            messages=messages,
            options=chat_request.options
        )
        return ChatResponse(
            model=result.get("model", model),
            message=result.get("message", {}),
            done=result.get("done", True)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat service unavailable: {str(e)}")