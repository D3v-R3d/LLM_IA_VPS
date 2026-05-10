"""
Google Gemini Provider

LLM provider implementation for Google Gemini API.
Uses OpenAI-compatible endpoint.
Tool formatting delegated to GoogleAdapter.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging

from app.services.llm.llm_provider import LLMProvider
from app.core.config import settings
from app.services.agent_tools.providers.adapters.google_adapter import GoogleAdapter

logger = logging.getLogger(__name__)


class GoogleProvider(LLMProvider):
    """
    Google Gemini API provider via OpenAI-compatible endpoint.

    Endpoint: https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.base_url = base_url or self.BASE_URL
        self._client = httpx.AsyncClient(timeout=180.0)
        self._adapter = GoogleAdapter()

    @property
    def name(self) -> str:
        return "google"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import logging
        logger = logging.getLogger(__name__)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if options:
            safe_options = {k: v for k, v in options.items() if k not in ("model", "messages", "stream")}
            payload.update(safe_options)

        response = await self._client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._get_headers()
        )
        if response.status_code != 200:
            logger.error(f"Google chat error: {response.status_code} body: {response.text[:1000]}")
        response.raise_for_status()
        result = response.json()

        return {
            "model": result.get("model", model),
            "message": result["choices"][0]["message"] if result.get("choices") else {},
            "done": True
        }

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import logging
        logger = logging.getLogger(__name__)
        # Tools from registry are already in OpenAI format (via get_all_definitions)
        # So we use them directly without adapter conversion
        provider_tools = tools
        payload = {
            "model": model,
            "messages": messages,
            "tools": provider_tools,
            "stream": False
        }
        if options:
            safe_options = {k: v for k, v in options.items() if k not in ("model", "messages", "tools", "stream")}
            payload.update(safe_options)

        # Debug: log payload size and first message
        logger.info(f"Google API payload: model={model}, messages={len(messages)}, tools={len(provider_tools)}")
        if messages:
            first_msg = messages[0] if isinstance(messages[0], dict) else str(messages[0])
            logger.debug(f"First message preview: {str(first_msg)[:200]}")

        response = await self._client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._get_headers()
        )
        if response.status_code != 200:
            logger.error(f"Google API error: {response.status_code} body: {response.text[:1000]}")
        response.raise_for_status()
        result = response.json()

        return {
            "model": result.get("model", model),
            "message": result["choices"][0]["message"] if result.get("choices") else {},
            "done": True
        }

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        """List available models from Google API."""
        response = await self._client.get(
            f"{self.base_url}/models",
            headers=self._get_headers()
        )
        response.raise_for_status()
        result = response.json()
        models = result.get("data", [])
        for m in models:
            if "id" in m:
                m["id"] = m["id"].removeprefix("models/")
        return models

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(
                f"{self.base_url}/models",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()