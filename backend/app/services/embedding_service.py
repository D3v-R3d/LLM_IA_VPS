from typing import List, Optional, Dict, Any
from app.services.chunking_service import ChunkingService
from app.services.llm_service import LLMService
from app.services.qdrant_service import QdrantService


class EmbeddingService:
    COLLECTION_NAME = "document_chunks"

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        embedding_model: str = "nomic-embed-text",
        vector_size: int = 768
    ):
        self.chunking_service = ChunkingService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.llm_service = LLMService()
        self.qdrant_service = QdrantService()
        self.embedding_model = embedding_model
        self.vector_size = vector_size

    def _ensure_collection_exists(self) -> bool:
        if not self.qdrant_service.collection_exists(self.COLLECTION_NAME):
            return self.qdrant_service.create_collection(
                collection_name=self.COLLECTION_NAME,
                vector_size=self.vector_size
            )
        return True

    async def embed_document(self, document: dict) -> Dict[str, Any]:
        document_id = document.get("id")
        content = document.get("content_raw", "")

        if not content:
            return {"chunks_processed": 0, "success": False}

        chunks = self.chunking_service.chunk_text(content, document_id)

        if not chunks:
            return {"chunks_processed": 0, "success": False}

        self._ensure_collection_exists()

        texts_to_embed = [chunk["text"] for chunk in chunks]
        embedding_result = await self.llm_service.embed(
            model=self.embedding_model,
            input=texts_to_embed
        )

        embeddings = embedding_result.get("embeddings", [])

        payloads = [
            {
                "text": chunk["text"],
                "chunk_index": chunk["chunk_index"],
                "document_id": chunk["document_id"],
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"]
            }
            for chunk in chunks
        ]

        success = self.qdrant_service.insert_vectors(
            collection_name=self.COLLECTION_NAME,
            vectors=embeddings,
            payloads=payloads
        )

        return {
            "chunks_processed": len(chunks),
            "success": success,
            "document_id": document_id
        }

    async def embed_documents(self, documents: List[dict]) -> Dict[str, Any]:
        total_chunks = 0
        successful_docs = 0

        for doc in documents:
            result = await self.embed_document(doc)
            if result["success"]:
                total_chunks += result["chunks_processed"]
                successful_docs += 1

        return {
            "total_chunks": total_chunks,
            "successful_docs": successful_docs,
            "total_documents": len(documents)
        }

    async def search_similar(
        self,
        query_text: str,
        limit: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        embedding_result = await self.llm_service.embed(
            model=self.embedding_model,
            input=query_text
        )

        query_embedding = embedding_result.get("embeddings", [[]])[0]

        results = self.qdrant_service.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )

        return results

    def health_check(self) -> Dict[str, bool]:
        return {
            "qdrant": self.qdrant_service.health_check(),
            "llm": True
        }