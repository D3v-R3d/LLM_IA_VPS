"""
Ollama Provider

LLM provider implementation for Ollama API.
Uses OpenAI-compatible format for tool calling.
Tool formatting delegated to OllamaAdapter (which reuses OpenAIAdapter).
"""

from typing import List, Dict, Any, Optional
import os
import httpx
import logging

from app.providers.llm.llm_provider import LLMProvider
from app.providers.llm.llm_base_client import LLMBaseClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider, LLMBaseClient):
    """Ollama LLM provider."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        use_cloud = os.environ.get("OLLAMA_USE_CLOUD", "false").lower() == "true"
        if base_url:
            self.base_url = base_url.rstrip("/")
        elif use_cloud:
            self.base_url = settings.OLLAMA_CLOUD_HOST.rstrip("/")
        else:
            self.base_url = settings.OLLAMA_HOST.rstrip("/")
        self.api_key = api_key or settings.OLLAMA_API_KEY
        LLMBaseClient.__init__(self, base_url=self.base_url, api_key=self.api_key)

    @property
    def name(self) -> str:
        return "ollama"

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            **(options or {})
        }
        response = await self.post("/api/chat", payload)
        return {
            "model": model,
            "message": response.get("message", {}),
            "done": response.get("done", True)
        }

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Tools from registry are already in OpenAI-compatible format
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            **(options or {})
        }
        response = await self.post("/api/chat", payload)
        return {
            "model": model,
            "message": response.get("message", {}),
            "done": response.get("done", True)
        }

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        try:
            result = await self.get("/api/tags")
            return [
                {"id": m.get("name"), "name": m.get("name"), "description": f"Ollama model: {m.get('name')}"}
                for m in result.get("models", [])
            ]
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            result = await self.get("/api/tags")
            return "models" in result
        except Exception:
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {"model": model, "prompt": prompt}
        if system:
            payload["system"] = system
        return await self.post("/api/generate", payload)