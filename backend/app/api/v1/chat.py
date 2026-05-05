from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.services.llm_service import LLMService
from app.core.config import settings


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
async def chat(request: ChatRequest):
    llm_service = LLMService(
        base_url=settings.OLLAMA_CLOUD_HOST,
        api_key=settings.OLLAMA_API_KEY
    )
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        result = await llm_service.chat(
            model=request.model,
            messages=messages,
            stream=request.stream
        )
        await llm_service.close()
        return ChatResponse(
            model=result.get("model", request.model),
            message=result.get("message", {}),
            done=result.get("done", True)
        )
    except Exception as e:
        await llm_service.close()
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")