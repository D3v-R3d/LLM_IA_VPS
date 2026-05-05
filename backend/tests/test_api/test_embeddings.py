import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestEmbeddingEndpoints:
    def test_embed_document_not_found(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        doc_response = client.post("/api/v1/documents", json=sample_document_data, params={"user_id": user_id})
        document_id = doc_response.json()["id"]

        with patch("app.api.v1.embeddings.document_service") as mock_doc_service:
            mock_doc_service.get_by_id.return_value = None

            response = client.post("/api/v1/embeddings/document", json={"document_id": str(document_id)})
            assert response.status_code == 404

    def test_embed_document_success(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        doc_response = client.post("/api/v1/documents", json=sample_document_data, params={"user_id": user_id})

        with patch("app.api.v1.embeddings.embedding_service") as mock_embedding_service:
            mock_embedding_service.embed_document = AsyncMock(return_value={
                "chunks_processed": 3,
                "success": True,
                "document_id": doc_response.json()["id"]
            })

            response = client.post("/api/v1/embeddings/document", json={"document_id": str(doc_response.json()["id"])})
            assert response.status_code == 200
            data = response.json()
            assert data["chunks_processed"] == 3
            assert data["success"] == True

    def test_search_similar(self, client: TestClient):
        with patch("app.api.v1.embeddings.embedding_service") as mock_embedding_service:
            mock_embedding_service.search_similar = AsyncMock(return_value=[
                {"id": "result1", "score": 0.95, "payload": {"text": "Found text", "chunk_index": 0}}
            ])

            response = client.post("/api/v1/embeddings/search", json={
                "query_text": "test query",
                "limit": 5
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["score"] == 0.95
            assert data["query_text"] == "test query"

    def test_search_similar_with_threshold(self, client: TestClient):
        with patch("app.api.v1.embeddings.embedding_service") as mock_embedding_service:
            mock_embedding_service.search_similar = AsyncMock(return_value=[])

            response = client.post("/api/v1/embeddings/search", json={
                "query_text": "test query",
                "limit": 5,
                "score_threshold": 0.8
            })
            assert response.status_code == 200

            mock_embedding_service.search_similar.assert_called_once()
            call_args = mock_embedding_service.search_similar.call_args
            assert call_args.kwargs["score_threshold"] == 0.8

    def test_embed_documents_empty_list(self, client: TestClient):
        with patch("app.api.v1.embeddings.embedding_service") as mock_embedding_service:
            mock_embedding_service.embed_documents = AsyncMock(return_value={
                "total_chunks": 0,
                "successful_docs": 0,
                "total_documents": 0
            })

            response = client.post("/api/v1/embeddings/documents", json={"document_ids": []})
            assert response.status_code == 200

    def test_embed_documents_partial_found(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        doc_response = client.post("/api/v1/documents", json=sample_document_data, params={"user_id": user_id})

        with patch("app.api.v1.embeddings.embedding_service") as mock_embedding_service:
            mock_embedding_service.embed_documents = AsyncMock(return_value={
                "total_chunks": 2,
                "successful_docs": 1,
                "total_documents": 2
            })

            response = client.post("/api/v1/embeddings/documents", json={
                "document_ids": [str(doc_response.json()["id"]), "00000000-0000-0000-0000-000000000000"]
            })
            assert response.status_code == 200

    def test_embeddings_health(self, client: TestClient):
        with patch("app.api.v1.embeddings.embedding_service") as mock_embedding_service:
            mock_embedding_service.health_check.return_value = {
                "qdrant": True,
                "llm": True
            }

            response = client.get("/api/v1/embeddings/health")
            assert response.status_code == 200
            data = response.json()
            assert data["qdrant"] == True
            assert data["llm"] == True