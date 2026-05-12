"""
Groq Provider

LLM provider implementation for Groq API.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging

from app.providers.llm.llm_provider import LLMProvider
from app.providers.llm.llm_base_client import LLMBaseClient
from app.providers.llm.http_client_pool import HttpClientPool
from app.core.config import settings
from app.providers.adapters.groq_adapter import GroqAdapter

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """Groq LLM provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self._adapter = GroqAdapter()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "groq"

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(300.0),
                base_url="https://api.groq.com/openai/v1",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
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
        payload = {
            "model": model,
            "messages": messages,
            **(options or {})
        }
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        client = self._get_client()
        # Tools from registry are already in OpenAI-compatible format
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            **(options or {})
        }
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            result = await client.get("/models")
            result.raise_for_status()
            data = result.json()
            return [
                {"id": m.get("id"), "name": m.get("id"), "description": m.get("description", "")}
                for m in data.get("data", [])
            ]
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            result = await client.get("/models")
            result.raise_for_status()
            return True
        except Exception:
            return False