"""
Anthropic Provider

LLM provider implementation for Anthropic Claude API.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging

from app.providers.llm.llm_provider import LLMProvider
from app.core.config import settings
from app.providers.adapters.anthropic_adapter import AnthropicAdapter

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._adapter = AnthropicAdapter()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(300.0),
                base_url="https://api.anthropic.com",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
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
            "max_tokens": 1024,
            **(options or {})
        }
        response = await client.post("/v1/messages", json=payload)
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
            "max_tokens": 1024,
            "tools": tools,
            **(options or {})
        }
        response = await client.post("/v1/messages", json=payload)
        response.raise_for_status()
        return self._adapter.parse_response(response.json())

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        try:
            return [
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "description": "Anthropic Claude 3.5 Sonnet"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "Anthropic Claude 3 Opus"},
                {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "description": "Anthropic Claude 3 Haiku"},
                {"id": "claude-3-5-haiku-20241021", "name": "Claude 3.5 Haiku", "description": "Anthropic Claude 3.5 Haiku"},
            ]
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            result = await client.post(
                "/v1/messages",
                json={"model": "claude-3-haiku-20240307", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
            )
            result.raise_for_status()
            return True
        except Exception:
            return False