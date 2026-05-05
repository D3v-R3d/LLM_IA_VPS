import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Helper to get auth headers."""
    response = client.post("/api/v1/users/login", json={"email": email, "password": password})
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


class TestEmbeddingEndpoints:
    def test_embed_document_not_found(self, client: TestClient, sample_user_data, sample_document_data):
        """Test 404 when document not found."""
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/documents", json=sample_document_data, headers=headers)

        with patch("app.api.v1.embeddings.DocumentService") as mock_doc_service_class:
            mock_doc_service = MagicMock()
            mock_doc_service.get_by_id.return_value = None
            mock_doc_service_class.return_value = mock_doc_service

            response = client.post(
                "/api/v1/embeddings/document",
                json={"document_id": "00000000-0000-0000-0000-000000000000"},
                headers=headers
            )
            assert response.status_code == 404

    def test_embed_document_success(self, client: TestClient, sample_user_data, sample_document_data):
        """Test successful document embedding."""
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        doc_response = client.post("/api/v1/documents", json=sample_document_data, headers=headers)
        document_id = doc_response.json()["id"]

        with patch("app.api.v1.embeddings.ChunkingService") as mock_chunking, \
             patch("app.api.v1.embeddings.VectorStorageService") as mock_vector_storage, \
             patch("app.api.v1.embeddings.get_embedding_service") as mock_get_embedding, \
             patch("app.api.v1.embeddings.DocumentService") as mock_doc_service_class:

            mock_doc_instance = MagicMock()
            mock_doc_instance.get_by_id.return_value = MagicMock(
                id=document_id,
                user_id=user_id,
                name="Test Doc",
                content_raw="Test content"
            )
            mock_doc_instance.mark_as_embedded.return_value = None
            mock_doc_service_class.return_value = mock_doc_instance

            mock_chunking_instance = MagicMock()
            mock_chunking_instance.chunk_text.return_value = [
                {"text": "chunk1", "chunk_index": 0, "start_char": 0, "end_char": 100, "document_id": str(document_id)}
            ]
            mock_chunking.return_value = mock_chunking_instance

            mock_vector_instance = MagicMock()
            mock_vector_instance.ensure_collection.return_value = True
            mock_vector_instance.insert_vectors.return_value = True
            mock_vector_storage.return_value = mock_vector_instance

            mock_embedding = MagicMock()
            mock_embedding.embed = AsyncMock(return_value={"embeddings": [[0.1] * 768]})
            mock_get_embedding.return_value = mock_embedding

            response = client.post(
                "/api/v1/embeddings/document",
                json={"document_id": str(document_id)},
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["chunks_processed"] == 1
            assert data["success"] == True

    def test_search_similar(self, client: TestClient, sample_user_data):
        """Test semantic search."""
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.embeddings.get_embedding_service") as mock_get_embedding, \
             patch("app.api.v1.embeddings.VectorStorageService") as mock_vector_storage_class:

            mock_embedding = MagicMock()
            mock_embedding.embed = AsyncMock(return_value={"embeddings": [[0.1] * 768]})
            mock_get_embedding.return_value = mock_embedding

            mock_vector_instance = MagicMock()
            mock_vector_instance.search.return_value = [
                {"id": "result1", "score": 0.95, "payload": {"text": "Found text", "chunk_index": 0}}
            ]
            mock_vector_storage_class.return_value = mock_vector_instance

            response = client.post(
                "/api/v1/embeddings/search",
                json={"query_text": "test query", "limit": 5},
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["score"] == 0.95
            assert data["query_text"] == "test query"

    def test_search_similar_with_threshold(self, client: TestClient, sample_user_data):
        """Test search with score threshold."""
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.api.v1.embeddings.get_embedding_service") as mock_get_embedding, \
             patch("app.api.v1.embeddings.VectorStorageService") as mock_vector_storage_class:

            mock_embedding = MagicMock()
            mock_embedding.embed = AsyncMock(return_value={"embeddings": [[0.1] * 768]})
            mock_get_embedding.return_value = mock_embedding

            mock_vector_instance = MagicMock()
            mock_vector_instance.search.return_value = []
            mock_vector_storage_class.return_value = mock_vector_instance

            response = client.post(
                "/api/v1/embeddings/search",
                json={"query_text": "test query", "limit": 5, "score_threshold": 0.8},
                headers=headers
            )
            assert response.status_code == 200
            mock_vector_instance.search.assert_called_once()
            call_args = mock_vector_instance.search.call_args
            assert call_args.kwargs["score_threshold"] == 0.8

    def test_embed_documents_empty_list(self, client: TestClient, sample_user_data):
        """Test embedding empty document list."""
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/v1/embeddings/documents",
            json={"document_ids": []},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 0

    def test_embed_documents_partial_found(self, client: TestClient, sample_user_data, sample_document_data):
        """Test embedding where some documents not found."""
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        doc_response = client.post("/api/v1/documents", json=sample_document_data, headers=headers)
        document_id = doc_response.json()["id"]

        with patch("app.api.v1.embeddings.ChunkingService") as mock_chunking, \
             patch("app.api.v1.embeddings.VectorStorageService") as mock_vector_storage, \
             patch("app.api.v1.embeddings.get_embedding_service") as mock_get_embedding, \
             patch("app.api.v1.embeddings.DocumentService") as mock_doc_service_class:

            mock_chunking_instance = MagicMock()
            mock_chunking_instance.chunk_text.return_value = []
            mock_chunking.return_value = mock_chunking_instance

            mock_vector_instance = MagicMock()
            mock_vector_instance.ensure_collection.return_value = True
            mock_vector_storage.return_value = mock_vector_instance

            mock_embedding = MagicMock()
            mock_embedding.embed = AsyncMock(return_value={"embeddings": []})
            mock_get_embedding.return_value = mock_embedding

            mock_doc_service = MagicMock()
            mock_doc_service.mark_as_embedded.return_value = None
            mock_doc_service_class.return_value = mock_doc_service

            response = client.post(
                "/api/v1/embeddings/documents",
                json={"document_ids": [str(document_id), "00000000-0000-0000-0000-000000000000"]},
                headers=headers
            )
            assert response.status_code == 200

    def test_embeddings_health(self, client: TestClient):
        """Test health check endpoint."""
        with patch("app.api.v1.embeddings.VectorStorageService") as mock_vector_storage_class:
            mock_vector_instance = MagicMock()
            mock_vector_instance.health_check.return_value = True
            mock_vector_storage_class.return_value = mock_vector_instance

            response = client.get("/api/v1/embeddings/health")
            assert response.status_code == 200
            data = response.json()
            assert data["qdrant"] == True
            assert data["llm"] == True