"""
LLM Provider Interface

Abstract base class for LLM providers.
All providers must implement this interface.
"""

import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Providers like Ollama, Groq, OpenAI must implement:
    - chat(): Send messages and get response
    - chat_with_tools(): Chat with function calling support
    - health_check(): Verify provider is reachable
    """

    _models_cache: Optional[List[Dict[str, Any]]] = None
    _models_cache_time: float = 0
    MODELS_CACHE_TTL: int = 60

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'ollama', 'groq')."""
        pass

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate chat completion.

        Args:
            model: Model name
            messages: List of message dicts with role and content
            options: Optional model parameters

        Returns:
            Response dict with assistant message
        """
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate chat completion with tool calling.

        Args:
            model: Model name
            messages: Message history
            tools: Tool definitions
            options: Optional model parameters

        Returns:
            LLM response with tool_calls if any
        """
        pass

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models with in-memory cache (60s TTL)."""
        now = time.time()
        if self._models_cache and (now - self._models_cache_time) < self.MODELS_CACHE_TTL:
            return self._models_cache

        models = await self._fetch_models()
        self._models_cache = models
        self._models_cache_time = now
        return models

    @abstractmethod
    async def _fetch_models(self) -> List[Dict[str, Any]]:
        """Provider-specific model fetching."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is reachable."""
        pass

    async def close(self):
        """Cleanup resources. Override if needed."""
        pass
