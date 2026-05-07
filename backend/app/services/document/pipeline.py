"""
Data Pipeline Service

Orchestrates the complete scraping -> cleaning -> chunking -> embedding -> storage pipeline.
"""

from typing import Dict, Any, List, Optional
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataPipelineService:
    """
    Orchestrator for scraping, cleaning, chunking, embedding, and storing data.

    Pipeline flow:
    1. Scrape URLs (ScrapingService)
    2. Clean text (TextCleaningService)
    3. Chunk text (ChunkingService)
    4. Create embeddings (EmbeddingService)
    5. Store in vector DB (VectorStorageService)
    """

    def __init__(self):
        from app.services.document.scraping import ScrapingService
        from app.services.document.chunking import ChunkingService
        from app.services.document.text_cleaning import TextCleaningService
        from app.services.llm.embedding import EmbeddingService
        from app.services.document.vector_storage import VectorStorageService

        self.scraping = ScrapingService()
        self.chunking = ChunkingService(chunk_size=500, chunk_overlap=50)
        self.text_cleaning = TextCleaningService()
        self.embedding = EmbeddingService()
        self.vector_storage = VectorStorageService()

    async def scrape_and_store(
        self,
        urls: List[str],
        collection_name: str = "web_content",
        user_id: Optional[str] = None,
        max_length: int = 10000,
        store_vectors: bool = True
    ) -> Dict[str, Any]:
        """
        Complete pipeline: scrape URLs -> clean -> chunk -> embed -> store.

        Args:
            urls: List of URLs to scrape
            collection_name: VectorDB collection name
            user_id: Optional user ID for tracking
            max_length: Max characters per URL content
            store_vectors: Whether to store embeddings (False for dry run)

        Returns:
            Dict with pipeline results:
            - total_urls: int
            - successful: int
            - failed: int
            - results: List[Dict] per URL with chunks_count, embeddings_count
        """
        logger.info(f"PIPELINE_START: urls={len(urls)}, collection={collection_name}")

        scraped = await self.scraping.fetch_multiple(urls, max_length=max_length, clean=True)

        results = []
        total_chunks = 0
        total_embeddings = 0
        successful = 0
        failed = 0

        for item in scraped:
            if not item.get("success"):
                failed += 1
                results.append({
                    "url": item.get("url"),
                    "success": False,
                    "error": item.get("error", "Unknown error")
                })
                continue

            url = item.get("url")
            content = item.get("content", "")

            if not content or len(content) < 50:
                failed += 1
                results.append({
                    "url": url,
                    "success": False,
                    "error": "Content too short or empty"
                })
                continue

            chunks = self.chunking.chunk_text(
                content,
                document_id=str(uuid.uuid4())
            )

            for chunk in chunks:
                chunk["url"] = url
                chunk["title"] = item.get("title", "")
                chunk["user_id"] = user_id
                chunk["scraped_at"] = datetime.utcnow().isoformat()

            total_chunks += len(chunks)

            if store_vectors:
                texts = [c["text"] for c in chunks]
                try:
                    embeddings = await self.embedding.embed_batch(texts)

                    if embeddings and len(embeddings) > 0:
                        self.vector_storage.ensure_collection(
                            collection_name,
                            vector_size=len(embeddings[0])
                        )

                        self.vector_storage.insert_vectors(
                            collection_name,
                            vectors=embeddings,
                            payloads=chunks
                        )
                        total_embeddings += len(embeddings)
                        successful += 1

                        logger.info(f"PIPELINE_ITEM_OK: url={url}, chunks={len(chunks)}, embeddings={len(embeddings)}")

                except Exception as e:
                    logger.error(f"PIPELINE_EMBEDDING_FAILED: url={url}, error={e}")
                    failed += 1
                    results.append({
                        "url": url,
                        "success": False,
                        "error": f"Embedding failed: {str(e)}",
                        "chunks_count": len(chunks)
                    })
                    continue
            else:
                total_embeddings += len(chunks)
                successful += 1

            results.append({
                "url": url,
                "success": True,
                "chunks_count": len(chunks),
                "embeddings_count": len(chunks),
                "content_length": len(content)
            })

        logger.info(f"PIPELINE_DONE: successful={successful}, failed={failed}, chunks={total_chunks}, embeddings={total_embeddings}")

        return {
            "total_urls": len(urls),
            "successful": successful,
            "failed": failed,
            "total_chunks": total_chunks,
            "total_embeddings": total_embeddings,
            "results": results
        }

    async def search_stored(
        self,
        query: str,
        collection_name: str = "web_content",
        limit: int = 5,
        score_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Search stored embeddings.

        Args:
            query: Search query text
            collection_name: VectorDB collection
            limit: Max results
            score_threshold: Minimum relevance score

        Returns:
            Dict with search results
        """
        try:
            vector = await self.embedding.embed_single(query)

            if not vector:
                return {"success": False, "error": "Failed to embed query"}

            results = self.vector_storage.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=limit,
                score_threshold=score_threshold
            )

            return {
                "success": True,
                "results": results
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"success": False, "error": str(e)}