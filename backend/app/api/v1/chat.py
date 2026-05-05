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
    model: str
    messages: List[Message]
    stream: bool = False
    options: Optional[dict] = None


class ChatResponse(BaseModel):
    model: str
    message: dict
    done: bool


@router.post("", response_model=ChatResponse)
@limiter.limit(os.environ.get("CHAT_RATE_LIMIT", "30/minute"))
async def chat(request: Request, chat_request: ChatRequest):
    llm_service = LLMService(
        base_url=settings.OLLAMA_CLOUD_HOST,
        api_key=settings.OLLAMA_API_KEY
    )
    try:
        messages = [{"role": m.role, "content": m.content} for m in chat_request.messages]
        result = await llm_service.chat(
            model=chat_request.model,
            messages=messages
        )
        await llm_service.close()
        return ChatResponse(
            model=result.get("model", request.model),
            message=result.get("message", {}),
            done=result.get("done", True)
        )
    except Exception as e:
        await llm_service.close()
        raise HTTPException(status_code=500, detail="Chat service unavailable")