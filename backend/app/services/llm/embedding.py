"""
Embedding Service

Generates text embeddings using Ollama API.
"""

from typing import List, Dict, Any, Optional, Union
from app.services.llm.llm_base import LLMBaseClient
from app.core.config import settings


class EmbeddingService:
    """
    Service for generating text embeddings.

    Uses Ollama's embedding models to convert text into
    numerical vectors for semantic search.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "nomic-embed-text"
    ):
        """
        Initialize embedding service.

        Args:
            base_url: Ollama server URL (local)
            model: Embedding model name
        """
        self.base_url = base_url or settings.OLLAMA_HOST
        self.model = model

    async def embed(
        self,
        input: Union[str, List[str]],
        truncate: bool = True
    ) -> Dict[str, Any]:
        """
        Generate embeddings for text.

        Args:
            input: Single text string or list of texts
            truncate: Truncate to fit model context

        Returns:
            API response with embeddings array

        Example:
            result = await service.embed("Hello world")
            embeddings = result.get("embeddings", [])
        """
        client = LLMBaseClient(self.base_url)
        try:
            payload = {
                "model": self.model,
                "input": input,
                "truncate": truncate
            }

            response = await client.client.post(
                f"{client.base_url}/api/embed",
                json=payload,
                headers=client._get_headers()
            )
            response.raise_for_status()
            return response.json()
        finally:
            await client.close()

    async def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        result = await self.embed(text)
        embeddings = result.get("embeddings", [])
        return embeddings[0] if embeddings else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        result = await self.embed(texts)
        return result.get("embeddings", [])

    async def list_models(self) -> List[str]:
        """
        List available embedding models.

        Returns:
            List of model names
        """
        client = LLMBaseClient(self.base_url)
        try:
            response = await client.client.get(
                f"{client.base_url}/api/tags",
                headers=client._get_headers()
            )
            response.raise_for_status()
            data = response.json()
            return [m.get("name") for m in data.get("models", [])]
        finally:
            await client.close()

    async def health_check(self) -> bool:
        """
        Check if embedding service is reachable.

        Returns:
            True if service is healthy
        """
        try:
            await self.embed("health check")
            return True
        except Exception:
            return False