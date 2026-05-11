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

from app.services.llm.llm_provider import LLMProvider
from app.core.config import settings
from app.services.agent_tools.providers.adapters.ollama_adapter import OllamaAdapter

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama API provider.

    API Reference: https://ollama.com/api
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        use_cloud = os.environ.get("OLLAMA_USE_CLOUD", "false").lower() == "true"
        if base_url:
            self.base_url = base_url.rstrip("/")
        elif use_cloud:
            self.base_url = settings.OLLAMA_CLOUD_HOST.rstrip("/")
        else:
            self.base_url = settings.OLLAMA_HOST.rstrip("/")
        self.api_key = api_key or settings.OLLAMA_API_KEY
        self._client = httpx.AsyncClient(timeout=180.0)
        self._adapter = OllamaAdapter()

    @property
    def name(self) -> str:
        return "ollama"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

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
        # Tools from registry are already in OpenAI format
        provider_tools = tools
        payload = {
            "model": model,
            "messages": messages,
            "tools": provider_tools,
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