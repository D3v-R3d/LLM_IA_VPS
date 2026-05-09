"""
Groq Provider

LLM provider implementation for Groq API.
API Reference: https://console.groq.com/docs/api-reference
"""

import json
from typing import List, Dict, Any, Optional
import httpx
from app.services.llm.llm_provider import LLMProvider
from app.core.config import settings


class GroqProvider(LLMProvider):
    """
    Groq API provider.

    Uses OpenAI-compatible endpoint: https://api.groq.com/openai/v1/chat/completions
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.base_url = base_url or self.BASE_URL
        self._client = httpx.AsyncClient(timeout=180.0)

    @property
    def name(self) -> str:
        return "groq"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request with auto-reconnect for closed clients."""
        for attempt in range(2):
            try:
                return await self._client.request(method, f"{self.base_url}{path}", **kwargs)
            except RuntimeError as e:
                if "closed" in str(e) and attempt == 0:
                    self._client = httpx.AsyncClient(timeout=180.0)
                    continue
                raise

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if options:
            safe_options = {k: v for k, v in options.items() if k not in ("model", "messages", "stream")}
            payload.update(safe_options)

        response = await self._request(
            "POST", "/chat/completions",
            json=payload,
            headers=self._get_headers()
        )
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
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False
        }
        if options:
            safe_options = {k: v for k, v in options.items() if k not in ("model", "messages", "tools", "stream")}
            payload.update(safe_options)

        response = await self._request(
            "POST", "/chat/completions",
            json=payload,
            headers=self._get_headers()
        )
        if response.status_code == 429:
            import logging
            logging.getLogger(__name__).error(f"Groq 429 body: {response.text[:500]}")
        elif response.status_code == 400:
            import logging
            logging.getLogger(__name__).error(f"Groq 400 body: {response.text[:500]}")
        elif response.status_code == 413:
            import logging
            logging.getLogger(__name__).error(f"Groq 413 body: {response.text[:500]}")
            payload_size = len(json.dumps(payload))
            logging.getLogger(__name__).error(f"Groq 413 payload size: {payload_size} bytes, messages: {len(messages)}, tools: {len(tools)}")
        response.raise_for_status()
        result = response.json()

        return {
            "model": result.get("model", model),
            "message": result["choices"][0]["message"] if result.get("choices") else {},
            "done": True
        }

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        """List available models from Groq API."""
        response = await self._request(
            "GET", "/models",
            headers=self._get_headers()
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", [])

    async def health_check(self) -> bool:
        try:
            response = await self._request(
                "GET", "/models",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        # Provider is a singleton cached by factory — don't actually close the client
        pass