"""
Google Tool Adapter

Reuses OpenAI adapter since Google Gemini uses OpenAI-compatible format.
"""

from app.services.agent_tools.providers.adapters.openai_adapter import OpenAIAdapter


class GoogleAdapter(OpenAIAdapter):
    """Adapter for Google Gemini provider (OpenAI-compatible)."""
    pass