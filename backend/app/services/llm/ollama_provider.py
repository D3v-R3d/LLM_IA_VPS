"""
Ollama Cloud Provider

LLM provider implementation for Ollama Cloud API.
"""

from typing import List, Dict, Any, Optional
import httpx
from app.services.llm.llm_provider import LLMProvider
from app.core.config import settings


class OllamaProvider(LLMProvider):
    """
    Ollama Cloud API provider.

    API Reference: https://ollama.com/api
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_HOST).rstrip("/")
        self.api_key = api_key or settings.OLLAMA_API_KEY
        self._client = httpx.AsyncClient(timeout=180.0)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

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
            "stream": False
        }
        if options:
            payload["options"] = options

        response = await self._client.post(
            f"{self.base_url}/api/chat",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import logging
        logger = logging.getLogger(__name__)
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False
        }
        if options:
            payload["options"] = options

        logger.info(f"Ollama chat_with_tools: url={self.base_url}/api/chat, model={model}, tools={len(tools)}")
        response = await self._client.post(
            f"{self.base_url}/api/chat",
            json=payload,
            headers=self._get_headers()
        )
        logger.info(f"Ollama response: status={response.status_code}")
        response.raise_for_status()
        result = response.json()

        return {
            "model": model,
            "message": result.get("message", {}),
            "done": result.get("done", True)
        }

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        """List available models from Ollama."""
        response = await self._client.get(
            f"{self.base_url}/api/tags",
            headers=self._get_headers()
        )
        response.raise_for_status()
        result = response.json()
        return result.get("models", [])

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(
                f"{self.base_url}/api/tags",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate text completion (non-chat models)."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system

        response = await self._client.post(
            f"{self.base_url}/api/generate",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()