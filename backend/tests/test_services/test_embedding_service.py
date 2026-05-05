import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    def test_init(self):
        service = EmbeddingService(
            chunk_size=100,
            chunk_overlap=20,
            embedding_model="test-model",
            vector_size=384
        )

        assert service.chunking_service.chunk_size == 100
        assert service.chunking_service.chunk_overlap == 20
        assert service.embedding_model == "test-model"
        assert service.vector_size == 384
        assert service.COLLECTION_NAME == "document_chunks"

    @pytest.mark.asyncio
    async def test_embed_document_empty_content(self):
        service = EmbeddingService()
        document = {"id": "test-id", "content_raw": ""}

        result = await service.embed_document(document)

        assert result["chunks_processed"] == 0
        assert result["success"] == False

    @pytest.mark.asyncio
    async def test_embed_document_no_content(self):
        service = EmbeddingService()
        document = {"id": "test-id"}

        result = await service.embed_document(document)

        assert result["chunks_processed"] == 0
        assert result["success"] == False

    @pytest.mark.asyncio
    async def test_embed_document_success(self):
        service = EmbeddingService()

        mock_embedding_result = {
            "embeddings": [
                [0.1, 0.2, 0.3] * 256,
                [0.4, 0.5, 0.6] * 256
            ]
        }

        with patch.object(service.llm_service, 'embed', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = mock_embedding_result

            with patch.object(service.qdrant_service, 'collection_exists', new_callable=MagicMock) as mock_exists:
                mock_exists.return_value = True

                with patch.object(service.qdrant_service, 'insert_vectors', new_callable=MagicMock) as mock_insert:
                    mock_insert.return_value = True

                    document = {
                        "id": "test-doc-id",
                        "name": "Test Document",
                        "content_raw": "This is a test document with enough content to create multiple chunks when split properly."
                    }

                    result = await service.embed_document(document)

                    assert result["success"] == True
                    assert result["chunks_processed"] >= 1
                    assert result["document_id"] == "test-doc-id"
                    mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_documents_multiple(self):
        service = EmbeddingService()

        mock_embedding_result = {"embeddings": [[0.1, 0.2, 0.3] * 256]}

        with patch.object(service.llm_service, 'embed', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = mock_embedding_result

            with patch.object(service.qdrant_service, 'collection_exists', new_callable=MagicMock) as mock_exists:
                mock_exists.return_value = True

                with patch.object(service.qdrant_service, 'insert_vectors', new_callable=MagicMock) as mock_insert:
                    mock_insert.return_value = True

                    documents = [
                        {"id": "doc1", "name": "Doc 1", "content_raw": "Content for document 1"},
                        {"id": "doc2", "name": "Doc 2", "content_raw": "Content for document 2"}
                    ]

                    result = await service.embed_documents(documents)

                    assert result["total_documents"] == 2
                    assert result["successful_docs"] == 2

    @pytest.mark.asyncio
    async def test_search_similar(self):
        service = EmbeddingService()

        mock_embedding_result = {"embeddings": [[0.1, 0.2, 0.3] * 256]}
        mock_search_results = [
            {"id": "result1", "score": 0.95, "payload": {"text": "Found text"}}
        ]

        with patch.object(service.llm_service, 'embed', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = mock_embedding_result

            with patch.object(service.qdrant_service, 'search', new_callable=MagicMock) as mock_search:
                mock_search.return_value = mock_search_results

                results = await service.search_similar("test query", limit=5)

                assert len(results) == 1
                assert results[0]["id"] == "result1"
                assert results[0]["score"] == 0.95
                mock_search.assert_called_once()

    def test_health_check(self):
        service = EmbeddingService()

        with patch.object(service.qdrant_service, 'health_check', return_value=True):
            health = service.health_check()

            assert "qdrant" in health
            assert "llm" in health

    def test_ensure_collection_exists_creates(self):
        service = EmbeddingService()

        with patch.object(service.qdrant_service, 'collection_exists', new_callable=MagicMock) as mock_exists:
            mock_exists.return_value = False

            with patch.object(service.qdrant_service, 'create_collection', new_callable=MagicMock) as mock_create:
                mock_create.return_value = True

                result = service._ensure_collection_exists()

                assert result == True
                mock_create.assert_called_once()

    def test_ensure_collection_exists_already_exists(self):
        service = EmbeddingService()

        with patch.object(service.qdrant_service, 'collection_exists', new_callable=MagicMock) as mock_exists:
            mock_exists.return_value = True

            result = service._ensure_collection_exists()

            assert result == True