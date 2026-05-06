"""
Chat Service

Chat completions using Ollama Cloud API.
"""

from typing import List, Dict, Any, Optional
from app.services.llm.llm_base import LLMBaseClient
from app.core.config import settings


class ChatService:
    """
    Service for generating chat completions.

    Uses Ollama Cloud API for chat completions with
    support for system prompts and message history.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize chat service.

        Args:
            base_url: Ollama Cloud base URL
            api_key: Ollama Cloud API key
        """
        self.base_url = base_url or settings.OLLAMA_CLOUD_HOST
        self.api_key = api_key or settings.OLLAMA_API_KEY

    async def close(self):
        """Close HTTP client (no-op, clients are closed per-request)."""
        pass

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate chat completion.

        Args:
            model: Model name (e.g., "gemma4:31b", "llama3.1")
            messages: List of message dicts with role and content
            options: Optional model parameters (temperature, seed, etc.)

        Returns:
            API response with assistant message

        Example messages format:
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ]
        """
        client = LLMBaseClient(self.base_url, self.api_key)
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False
            }

            if options:
                payload["options"] = options

            response = await client.client.post(
                f"{client.base_url}/api/chat",
                json=payload,
                headers=client._get_headers()
            )
            response.raise_for_status()
            return response.json()
        finally:
            await client.close()

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Generate chat completion with tool calling (single call, no auto-execution).

        Args:
            model: Model name with tool support
            messages: Message history
            tools: Tool definitions
            options: Optional model parameters
            max_iterations: Max tool call iterations (ignored, single call)

        Returns:
            LLM response with tool_calls if any
        """
        client = LLMBaseClient(self.base_url, self.api_key)

        try:
            payload = {
                "model": model,
                "messages": messages,
                "tools": tools,
                "stream": False
            }

            if options:
                payload["options"] = options

            response = await client.client.post(
                f"{client.base_url}/api/chat",
                json=payload,
                headers=client._get_headers()
            )
            response.raise_for_status()
            result = response.json()

            return {
                "model": model,
                "message": result.get("message", {}),
                "done": result.get("done", True)
            }
        finally:
            await client.close()

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate text completion (non-chat models).

        Args:
            model: Model name
            prompt: Input prompt
            system: Optional system message

        Returns:
            API response with generated text
        """
        client = LLMBaseClient(self.base_url, self.api_key)
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }

            if system:
                payload["system"] = system

            response = await client.client.post(
                f"{client.base_url}/api/generate",
                json=payload,
                headers=client._get_headers()
            )
            response.raise_for_status()
            return response.json()
        finally:
            await client.close()

    async def health_check(self) -> bool:
        """
        Check if chat service is reachable.

        Returns:
            True if service is healthy
        """
        client = LLMBaseClient(self.base_url, self.api_key)
        try:
            response = await client.client.get(
                f"{client.base_url}/api/tags",
                headers=client._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False
        finally:
            await client.close()