"""
Google Provider

LLM provider implementation for Google Gemini API.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging

from app.providers.llm.llm_provider import LLMProvider
from app.providers.llm.llm_base_client import LLMBaseClient
from app.core.config import settings
from app.providers.adapters.google_adapter import GoogleAdapter

logger = logging.getLogger(__name__)


class GoogleProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self._adapter = GoogleAdapter()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "google"

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(300.0),
                base_url="https://generativelanguage.googleapis.com/v1beta",
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
            "contents": formatted,
            **(options or {})
        }
        response = await client.post(
            f"/models/{model}:generateContent",
            params={"key": self.api_key},
            json=payload
        )
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
            "contents": formatted,
            "tools": tools,
            **(options or {})
        }
        response = await client.post(
            f"/models/{model}:generateContent",
            params={"key": self.api_key},
            json=payload
        )
        response.raise_for_status()
        return self._adapter.parse_response(response.json())

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        try:
            client = self._get_client()
            result = await client.get(
                "/models",
                params={"key": self.api_key}
            )
            result.raise_for_status()
            data = result.json()
            return [
                {"id": m.get("name", "").split("/")[-1], "name": m.get("displayName", ""), "description": m.get("description", "")}
                for m in data.get("models", [])
            ]
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            result = await client.get("/models", params={"key": self.api_key})
            result.raise_for_status()
            return True
        except Exception:
            return False