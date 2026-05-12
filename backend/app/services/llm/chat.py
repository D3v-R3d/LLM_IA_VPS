"""
Chat Service

Chat completions using configurable LLM provider (Ollama, Groq, etc.).
Delegates to LLMProviderFactory for provider management.
"""

from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.providers.llm.provider_factory import get_llm_provider


class ChatService:
    """
    Service for generating chat completions.

    Uses LLMProviderFactory to delegate to the configured provider.
    Supports Ollama Cloud, Groq, and other providers.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None
    ):
        self._provider_name = provider or getattr(settings, 'LLM_PROVIDER', 'ollama')
        # If base_url/api_key provided, create fresh provider (not cached)
        if base_url or api_key:
            self._fresh = True
            from app.providers.llm.ollama_provider import OllamaProvider
            self._provider = OllamaProvider(
                base_url=base_url or settings.OLLAMA_HOST,
                api_key=api_key or getattr(settings, 'OLLAMA_API_KEY', ''),
            )
        else:
            self._fresh = False
            self._provider = get_llm_provider(self._provider_name)

    async def close(self):
        """Close provider connection if needed."""
        if self._fresh:
            await self._provider.close()

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return await self._provider.chat(model, messages, options)

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        return await self._provider.chat_with_tools(model, messages, tools, options)

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        if hasattr(self._provider, 'generate'):
            return await self._provider.generate(model, prompt, system)
        raise NotImplementedError(f"Provider {self._provider_name} does not support generate")

    async def health_check(self) -> bool:
        return await self._provider.health_check()