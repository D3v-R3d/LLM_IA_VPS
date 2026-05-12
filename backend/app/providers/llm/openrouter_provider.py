"""
OpenRouter Provider

LLM provider implementation for OpenRouter API.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging

from app.providers.llm.llm_provider import LLMProvider
from app.core.config import settings
from app.providers.adapters.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    """OpenRouter LLM provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self._adapter = OpenAIAdapter()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "openrouter"

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(300.0),
                base_url="https://openrouter.ai",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://tower.ai",
                    "X-Title": "Tower",
                }
            )
        return self._client

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        client = self._get_client()
        formatted = self._adapter.format_messages(messages)
        payload = {
            "model": model,
            "messages": formatted,
            **(options or {})
        }
        response = await client.post("/api/v1/chat/completions", json=payload)
        response.raise_for_status()
        return self._adapter.parse_response(response.json())

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        client = self._get_client()
        formatted = self._adapter.format_messages(messages)
        # Tools from registry are already in correct format
        payload = {
            "model": model,
            "messages": formatted,
            "tools": tools,
            **(options or {})
        }
        response = await client.post("/api/v1/chat/completions", json=payload)
        response.raise_for_status()
        return self._adapter.parse_response(response.json())

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            result = await client.get("/api/v1/models")
            result.raise_for_status()
            data = result.json()
            return [
                {"id": m.get("id"), "name": m.get("name", m.get("id", "")), "description": m.get("description", "")}
                for m in data.get("data", [])
            ]
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            result = await client.get("/api/v1/models")
            result.raise_for_status()
            return True
        except Exception:
            return False