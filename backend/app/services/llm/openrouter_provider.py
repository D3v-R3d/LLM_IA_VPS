"""
OpenRouter Provider

LLM provider implementation for OpenRouter API.
API Reference: https://openrouter.ai/docs/api
Uses OpenAI-compatible endpoint.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.services.llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter API provider.
    
    Uses OpenAI-compatible endpoint: https://openrouter.ai/api/v1/chat/completions
    Supports various models including openai/gpt-oss-120b:free
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url or self.BASE_URL
        self._client = httpx.AsyncClient(timeout=180.0)

    @property
    def name(self) -> str:
        return "openrouter"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://tower.srv1632761.hstgr.cloud",
            "X-Title": "Tower AI Assistant"
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

        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            response.raise_for_status()

        data = response.json()
        return {
            "content": data["choices"][0]["message"]["content"]
        }

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "stream": False
        }

        if tools:
            payload["tools"] = tools

        if options:
            safe_options = {k: v for k, v in options.items() if k not in ("model", "messages", "stream")}
            payload.update(safe_options)

        response = await self._request(
            "POST", "/chat/completions",
            json=payload,
            headers=self._get_headers()
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            raise Exception(f"OpenRouter chat_with_tools error: {error_msg}")

        data = response.json()

        tool_calls = []
        if "choices" in data and len(data["choices"]) > 0:
            message = data["choices"][0].get("message", {})
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    tool_calls.append({
                        "id": tc.get("id", f"call_{tc.get('function', {}).get('name', 'unknown')}"),
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", "{}")
                        }
                    })

        return {
            "message": {
                "content": message.get("content", ""),
                "tool_calls": tool_calls
            }
        }

    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convert messages to OpenAI format."""
        converted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "tool":
                converted.append({
                    "role": "user",
                    "content": f"Tool result: {content}"
                })
            else:
                if isinstance(content, list):
                    text_content = ""
                    for c in content:
                        if c.get("type") == "text":
                            text_content += c.get("text", "")
                        elif c.get("type") == "tool_use":
                            text_content += f"[Tool: {c.get('name', 'unknown')}]"
                        elif c.get("type") == "tool_result":
                            text_content += f"[Result: {c.get('content', '')}]"
                    converted.append({"role": role, "content": text_content})
                else:
                    converted.append({"role": role, "content": str(content) if content else ""})

        return converted

    async def list_models(self) -> List[Dict]:
        """List available models."""
        response = await self._request(
            "GET", "/models",
            headers=self._get_headers()
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter list_models error: {response.status_code}")
            return []

        data = response.json()
        return data.get("data", [])

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        """Provider-specific model fetching."""
        models = await self.list_models()
        return [
            {"id": m.get("id"), "name": m.get("id")} 
            for m in models
        ]

    async def health_check(self) -> bool:
        """Check if provider is reachable."""
        try:
            response = await self._request(
                "GET", "/models",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()