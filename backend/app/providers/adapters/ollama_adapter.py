"""
Ollama Tool Adapter

Reuses OpenAI adapter since Ollama uses OpenAI-compatible format.
"""

from app.providers.adapters.openai_adapter import OpenAIAdapter


class OllamaAdapter(OpenAIAdapter):
    """Adapter for Ollama provider (OpenAI-compatible)."""
    pass