"""
Wrapper sync around EmbeddingService.
"""

from typing import List
from app.services.llm.embedding import EmbeddingService

VECTOR_SIZE = 768


class EmbeddingsWrapper:
    """
    Sync wrapper for EmbeddingService.
    """

    def __init__(self, base_url: str | None = None, model: str = "nomic-embed-text"):
        self._svc = None
        self._base_url = base_url
        self._model = model

    @property
    def svc(self):
        if self._svc is None:
            self._svc = EmbeddingService(base_url=self._base_url, model=self._model)
        return self._svc

    def embed(self, text: str) -> List[float]:
        """
        Embed a single text.
        """
        emb = self.svc.embed_single(text)
        if not emb:
            raise RuntimeError("EmbeddingService returned empty result")

        if len(emb) >= VECTOR_SIZE:
            return emb[:VECTOR_SIZE]

        if len(emb) > 0:
            ratio = VECTOR_SIZE / len(emb)
            extended = []
            for i in range(VECTOR_SIZE):
                extended.append(emb[int(i / ratio) % len(emb)])
            return extended

        raise RuntimeError("EmbeddingService returned empty result")


_embeddings_instance: EmbeddingsWrapper | None = None


def get_embeddings() -> EmbeddingsWrapper:
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = EmbeddingsWrapper()
    return _embeddings_instance
