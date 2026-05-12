"""
Groq Tool Adapter

Reuses OpenAI adapter since Groq uses OpenAI-compatible format.
"""

from app.providers.adapters.openai_adapter import OpenAIAdapter


class GroqAdapter(OpenAIAdapter):
    """Adapter for Groq provider (OpenAI-compatible)."""
    pass