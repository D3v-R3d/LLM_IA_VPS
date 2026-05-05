"""
LLM (Large Language Model) Service Module

This module provides integration with the Ollama Cloud API for text generation,
chat completion, and embedding generation. It uses httpx for async HTTP requests.

API Reference:
- Generate: POST /api/generate
- Chat: POST /api/chat
- Embed: POST /api/embed
- List Models: GET /api/tags

Authentication:
- Ollama Cloud uses Bearer token authentication
- Set OLLAMA_API_KEY environment variable
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service class for interacting with Ollama API (local or cloud).

    This class provides methods for:
    - Generating text completions (generate)
    - Generating chat completions (chat)
    - Generating embeddings (embed)
    - Listing available models (list_models)
    - Health checking the Ollama service

    Attributes:
        base_url: Base URL of the Ollama API server
        api_key: API key for Ollama Cloud authentication
        client: httpx AsyncClient for making HTTP requests
    """

    def __init__(self, base_url: str = None, api_key: str = None):
        """
        Initialize the LLM service.

        Args:
            base_url: Base URL for the Ollama API.
                      Defaults to local Ollama if not provided.
            api_key: API key for Ollama Cloud authentication.
                     Only needed for cloud mode.
        """
        self.base_url = base_url or "http://ollama:11434"
        self.api_key = api_key

        self.client = httpx.AsyncClient(timeout=60.0)

    def _get_headers(self) -> Dict[str, str]:
        """
        Build request headers including authentication.

        Returns:
            Dict of HTTP headers with Content-Type and Bearer token.
        """
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a text completion using the Ollama API.

        Sends a prompt to the specified model and returns the generated text.
        This is useful for tasks like text completion, code generation, etc.

        Args:
            model: Name of the model to use (e.g., "llama3.2", "mistral")
            prompt: The prompt text to generate from
            system: Optional system message to override model's default behavior
            options: Optional dict of model parameters (temperature, seed, etc.)
            stream: If True, returns a streaming response

        Returns:
            Dict containing the API response with generated text and metadata:
            - model: Model name used
            - response: Generated text
            - done: Boolean indicating completion
            - total_duration: Time spent generating (nanoseconds)
            - eval_count: Number of tokens in response

        API Endpoint: POST /api/generate
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }

        if system:
            payload["system"] = system

        if options:
            payload["options"] = options

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def chat(
        self,
        model: str,
        messages: list,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a chat completion using the Ollama API.

        Sends a conversation with multiple messages and returns the model's reply.
        Supports system messages, user messages, and assistant messages.

        Args:
            model: Name of the model to use (e.g., "llama3.2", "llama3.1")
            messages: List of message dicts with 'role' and 'content' keys
                     Roles: "system", "user", "assistant"
            options: Optional dict of model parameters
            stream: If True, returns a streaming response

        Returns:
            Dict containing the API response:
            - model: Model name used
            - message: Dict with 'role' and 'content' of assistant's reply
            - done: Boolean indicating completion

        API Endpoint: POST /api/chat
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }

        if options:
            payload["options"] = options

        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def embed(
        self,
        model: str,
        input: str | list,
        truncate: bool = True
    ) -> Dict[str, Any]:
        """
        Generate embeddings for text using the Ollama API.

        Converts text into numerical vectors that represent semantic meaning.
        Useful for similarity search, clustering, and RAG applications.

        Args:
            model: Name of the embedding model to use (e.g., "nomic-embed-text")
            input: Text string or list of text strings to embed
            truncate: If True, truncates input to fit within model's context length

        Returns:
            Dict containing:
            - embeddings: List of embedding vectors (one per input)

        API Endpoint: POST /api/embed
        """
        payload = {
            "model": model,
            "input": input,
            "truncate": truncate
        }

        response = await self.client.post(
            f"{self.base_url}/api/embed",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def list_models(self) -> Dict[str, Any]:
        """
        List all available models on the Ollama server.

        Returns:
            Dict containing:
            - models: List of model objects with name, size, modified_at, etc.

        API Endpoint: GET /api/tags
        """
        response = await self.client.get(
            f"{self.base_url}/api/tags",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def health_check(self) -> bool:
        """
        Check if the Ollama service is healthy and reachable.

        Returns:
            True if the service is reachable, False otherwise.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/tags",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """
        Close the HTTP client and release resources.
        """
        await self.client.aclose()

    async def chat_with_tools(
        self,
        model: str,
        messages: list,
        tools: list,
        options: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Generate a chat completion with tool calling support.

        The model can call tools (search, fetch, api) and the service
        executes them, feeding results back to the model until complete.

        Args:
            model: Name of the model to use
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions from ToolsService
            options: Optional model parameters
            max_iterations: Max number of tool calls (prevents infinite loops)

        Returns:
            Dict with final response and tool calls made

        API Endpoint: POST /api/chat with tools
        """
        from app.services.tools_service import ToolsService

        tools_service = ToolsService()
        iteration = 0

        current_messages = list(messages)

        while iteration < max_iterations:
            iteration += 1

            payload = {
                "model": model,
                "messages": current_messages,
                "tools": tools,
                "stream": False
            }

            if options:
                payload["options"] = options

            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers=self._get_headers()
            )

            try:
                response.raise_for_status()
                result = response.json()
            except Exception as e:
                logger.error(f"JSON parse error: {e}, response text: {response.text[:500]}")
                return {
                    "model": model,
                    "message": {"role": "assistant", "content": f"Error: {str(e)}"},
                    "iterations": iteration,
                    "message_history": current_messages
                }

            current_messages.append(result.get("message", {}))

            if not result.get("done", True):
                break

            tool_calls = result.get("message", {}).get("tool_calls", [])
            if not tool_calls:
                break

            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name")
                arguments = func.get("arguments", {})

                tool_result = await tools_service.execute_tool(tool_name, arguments)

                current_messages.append({
                    "role": "tool",
                    "content": str(tool_result),
                    "tool_call_id": tool_call.get("id")
                })

        return {
            "model": model,
            "message": current_messages[-1] if current_messages else {},
            "iterations": iteration,
            "message_history": current_messages
        }