"""
LLM Provider Factory

Creates and manages LLM providers based on configuration.
Supports Ollama, Groq, and other providers via the LLMProvider interface.
"""

from typing import Optional, Dict
from app.core.config import settings

from app.services.llm.llm_provider import LLMProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.google_provider import GoogleProvider
from app.services.llm.anthropic_provider import AnthropicProvider


class LLMProviderFactory:
    """
    Factory for creating LLM providers.

    Usage:
        factory = LLMProviderFactory()
        provider = factory.get_provider("ollama")  # or "groq"
        response = await provider.chat_with_tools(model="...", messages=[...], tools=[...])
    """

    _providers: Dict[str, LLMProvider] = {}
    _default: Optional[str] = None

    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> LLMProvider:
        """
        Get a provider by name or default.

        Args:
            name: Provider name ("ollama", "groq") or None for default

        Returns:
            LLMProvider instance
        """
        provider_name = name or cls.get_default_provider()

        if provider_name not in cls._providers:
            cls._providers[provider_name] = cls._create_provider(provider_name)

        return cls._providers[provider_name]

    @classmethod
    def _create_provider(cls, name: str) -> LLMProvider:
        """Create a new provider instance."""
        if name == "ollama":
            return OllamaProvider()
        elif name == "groq":
            return GroqProvider()
        elif name == "google":
            return GoogleProvider()
        elif name == "anthropic":
            return AnthropicProvider()
        else:
            raise ValueError(f"Unknown provider: {name}. Available: ollama, groq, google, anthropic")

    @classmethod
    def get_default_provider(cls) -> str:
        """Get the default provider from settings."""
        if cls._default:
            return cls._default
        return settings.LLM_PROVIDER

    @classmethod
    def list_providers(cls) -> list:
        """List available provider names."""
        return ["ollama", "groq", "google", "anthropic"]

    @classmethod
    def get_default_provider_name(cls) -> str:
        """Get the default provider name."""
        return cls.get_default_provider()

    @classmethod
    def clear_cache(cls):
        """Clear provider cache (useful for testing)."""
        cls._providers.clear()


def get_llm_provider(name: Optional[str] = None) -> LLMProvider:
    """Convenience function to get a provider."""
    return LLMProviderFactory.get_provider(name)


provider_factory = LLMProviderFactory()