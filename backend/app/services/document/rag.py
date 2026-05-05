"""
RAG Service

Retrieval Augmented Generation for conversation context.
Searches similar messages from vector storage.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID


class RAGService:
    """
    Service for retrieval augmented generation.

    Searches embeddings to find relevant context for LLM responses.
    """

    def __init__(self):
        from app.services.document.vector_storage import VectorStorageService
        self.vector_storage = VectorStorageService()
        self.collection_name = "message_embeddings"

    async def search_similar(
        self,
        query: str,
        limit: int = 5,
        conversation_id: Optional[UUID] = None,
        exclude_message_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar messages using semantic search.

        Args:
            query: Text to search for
            limit: Max number of results
            conversation_id: Filter by conversation (optional)
            exclude_message_id: Message to exclude from results (optional)

        Returns:
            List of similar messages with scores
        """
        try:
            from app.services.llm import EmbeddingService
            embedding_service = EmbeddingService()
            query_vector = await embedding_service.embed_single(query)

            if not query_vector:
                return []

            if not self.vector_storage.collection_exists(self.collection_name):
                return []

            results = self.vector_storage.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.5
            )

            filtered_results = []
            for r in results:
                payload = r.get("payload", {})
                if conversation_id and str(payload.get("conversation_id")) != str(conversation_id):
                    continue
                if exclude_message_id and str(payload.get("message_id")) == str(exclude_message_id):
                    continue
                filtered_results.append({
                    "message_id": payload.get("message_id"),
                    "conversation_id": payload.get("conversation_id"),
                    "role": payload.get("role"),
                    "content": payload.get("content"),
                    "score": r.get("score")
                })

            return filtered_results

        except Exception:
            return []

    def format_context(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format retrieved messages as context string.

        Args:
            messages: List of message dicts

        Returns:
            Formatted context string
        """
        if not messages:
            return ""

        context_parts = ["Related conversation context:"]
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            context_parts.append(f"- [{role}]: {content}")

        return "\n".join(context_parts)