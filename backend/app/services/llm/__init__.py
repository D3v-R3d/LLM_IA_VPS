"""
LLM Services

Chat and embedding services for LLM interactions:
- ChatService: Chat completions with Ollama Cloud
- EmbeddingService: Text embeddings with Ollama

Usage:
    from app.services.llm import ChatService, EmbeddingService
"""

from app.services.llm.chat import ChatService
from app.services.llm.embedding import EmbeddingService

__all__ = ["ChatService", "EmbeddingService"]