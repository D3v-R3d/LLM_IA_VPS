import pytest
from unittest.mock import MagicMock, patch
from app.services.document.vector_storage import VectorStorageService


class TestVectorStorageService:
    """Tests for VectorStorageService (Qdrant wrapper)."""

    @pytest.fixture
    def mock_qdrant_client(self):
        with patch('app.services.document.vector_storage.QdrantClient') as mock_client:
            yield mock_client

    @pytest.fixture
    def service(self, mock_qdrant_client):
        return VectorStorageService(url="http://localhost:6333", port=6333)

    def test_init_default(self):
        """Test service initialization with defaults."""
        service = VectorStorageService()
        assert service.url == "http://qdrant:6333"
        assert service.port == 6333

    def test_init_custom(self, mock_qdrant_client):
        """Test service initialization with custom values."""
        service = VectorStorageService(url="http://custom:6334", port=6334)
        assert service.url == "http://custom:6334"
        assert service.port == 6334

    def test_create_collection_success(self, service, mock_qdrant_client):
        """Test successful collection creation."""
        mock_qdrant_client.return_value.create_collection = MagicMock()
        result = service.create_collection("test_collection", vector_size=768, distance="COSINE")
        assert result is True
        mock_qdrant_client.return_value.create_collection.assert_called_once()

    def test_create_collection_failure(self, service, mock_qdrant_client):
        """Test failed collection creation."""
        mock_qdrant_client.return_value.create_collection = MagicMock(side_effect=Exception("Already exists"))
        result = service.create_collection("existing_collection")
        assert result is False

    def test_collection_exists_true(self, service, mock_qdrant_client):
        """Test collection exists returns True."""
        mock_qdrant_client.return_value.get_collection = MagicMock()
        result = service.collection_exists("my_collection")
        assert result is True

    def test_collection_exists_false(self, service, mock_qdrant_client):
        """Test collection exists returns False."""
        mock_qdrant_client.return_value.get_collection = MagicMock(side_effect=Exception("Not found"))
        result = service.collection_exists("nonexistent")
        assert result is False

    def test_ensure_collection_creates_if_not_exists(self, service, mock_qdrant_client):
        """Test ensure_collection creates collection if it doesn't exist."""
        mock_qdrant_client.return_value.get_collection = MagicMock(side_effect=Exception("Not found"))
        mock_qdrant_client.return_value.create_collection = MagicMock()
        result = service.ensure_collection("new_collection", vector_size=768)
        assert result is True
        mock_qdrant_client.return_value.create_collection.assert_called_once()

    def test_ensure_collection_returns_true_if_exists(self, service, mock_qdrant_client):
        """Test ensure_collection returns True if collection exists."""
        mock_qdrant_client.return_value.get_collection = MagicMock()
        result = service.ensure_collection("existing_collection", vector_size=768)
        assert result is True
        mock_qdrant_client.return_value.create_collection.assert_not_called()

    def test_insert_vectors_success(self, service, mock_qdrant_client):
        """Test successful vector insertion."""
        mock_qdrant_client.return_value.upsert = MagicMock()
        vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        payloads = [{"text": "first"}, {"text": "second"}]
        result = service.insert_vectors("test_collection", vectors, payloads)
        assert result is True
        mock_qdrant_client.return_value.upsert.assert_called_once()

    def test_insert_vectors_no_payloads(self, service, mock_qdrant_client):
        """Test vector insertion without payloads."""
        mock_qdrant_client.return_value.upsert = MagicMock()
        vectors = [[0.1, 0.2, 0.3]]
        result = service.insert_vectors("test_collection", vectors)
        assert result is True

    def test_insert_vectors_failure(self, service, mock_qdrant_client):
        """Test failed vector insertion."""
        mock_qdrant_client.return_value.upsert = MagicMock(side_effect=Exception("Connection error"))
        result = service.insert_vectors("test_collection", [[0.1, 0.2]])
        assert result is False

    def test_search_success(self, service, mock_qdrant_client):
        """Test successful search."""
        mock_result = MagicMock()
        mock_result.id = "point-1"
        mock_result.score = 0.95
        mock_result.payload = {"text": "test"}
        mock_qdrant_client.return_value.search = MagicMock(return_value=[mock_result])

        results = service.search("test_collection", [0.1, 0.2, 0.3], limit=5)
        assert len(results) == 1
        assert results[0]["id"] == "point-1"
        assert results[0]["score"] == 0.95

    def test_search_with_threshold(self, service, mock_qdrant_client):
        """Test search with score threshold."""
        mock_qdrant_client.return_value.search = MagicMock(return_value=[])
        results = service.search("test_collection", [0.1], limit=5, score_threshold=0.9)
        assert len(results) == 0

    def test_search_failure(self, service, mock_qdrant_client):
        """Test failed search returns empty list."""
        mock_qdrant_client.return_value.search = MagicMock(side_effect=Exception("Search failed"))
        results = service.search("test_collection", [0.1])
        assert results == []

    def test_scroll_points_success(self, service, mock_qdrant_client):
        """Test scrolling through points."""
        mock_point = MagicMock()
        mock_point.id = "point-1"
        mock_point.vector = [0.1, 0.2]
        mock_point.payload = {"text": "test"}
        mock_scroll_result = MagicMock()
        mock_scroll_result.points = [mock_point]
        mock_scroll_result.next_page_offset = "offset-123"
        mock_qdrant_client.return_value.scroll = MagicMock(return_value=mock_scroll_result)

        result = service.scroll_points("test_collection", limit=100)
        assert len(result["points"]) == 1
        assert result["next_page_offset"] == "offset-123"

    def test_scroll_points_failure(self, service, mock_qdrant_client):
        """Test scroll points failure."""
        mock_qdrant_client.return_value.scroll = MagicMock(side_effect=Exception("Scroll failed"))
        result = service.scroll_points("test_collection")
        assert result == {"points": [], "next_page_offset": None}

    def test_count_points_success(self, service, mock_qdrant_client):
        """Test counting points."""
        mock_count_result = MagicMock()
        mock_count_result.count = 42
        mock_qdrant_client.return_value.count = MagicMock(return_value=mock_count_result)

        count = service.count_points("test_collection")
        assert count == 42

    def test_count_points_failure(self, service, mock_qdrant_client):
        """Test count points failure."""
        mock_qdrant_client.return_value.count = MagicMock(side_effect=Exception("Count failed"))
        count = service.count_points("test_collection")
        assert count == 0

    def test_get_point_success(self, service, mock_qdrant_client):
        """Test getting a single point."""
        mock_point = MagicMock()
        mock_point.id = "point-1"
        mock_point.vector = [0.1, 0.2]
        mock_point.payload = {"text": "test"}
        mock_qdrant_client.return_value.retrieve = MagicMock(return_value=[mock_point])

        result = service.get_point("test_collection", "point-1")
        assert result["id"] == "point-1"
        assert result["payload"]["text"] == "test"

    def test_get_point_not_found(self, service, mock_qdrant_client):
        """Test getting a point that doesn't exist."""
        mock_qdrant_client.return_value.retrieve = MagicMock(return_value=[])
        result = service.get_point("test_collection", "nonexistent")
        assert result is None

    def test_search_batch_success(self, service, mock_qdrant_client):
        """Test batch search."""
        mock_result = MagicMock()
        mock_result.id = "point-1"
        mock_result.score = 0.9
        mock_result.payload = {"text": "test"}
        mock_qdrant_client.return_value.search_batch = MagicMock(return_value=[[mock_result], [mock_result]])

        results = service.search_batch("test_collection", [[0.1, 0.2], [0.3, 0.4]], limit=5)
        assert len(results) == 2
        assert len(results[0]) == 1

    def test_delete_collection_success(self, service, mock_qdrant_client):
        """Test deleting a collection."""
        mock_qdrant_client.return_value.delete_collection = MagicMock()
        result = service.delete_collection("test_collection")
        assert result is True

    def test_delete_collection_failure(self, service, mock_qdrant_client):
        """Test deleting a collection failure."""
        mock_qdrant_client.return_value.delete_collection = MagicMock(side_effect=Exception("Delete failed"))
        result = service.delete_collection("test_collection")
        assert result is False

    def test_get_collection_info_success(self, service, mock_qdrant_client):
        """Test getting collection info."""
        mock_info = MagicMock()
        mock_info.vectors_count = 100
        mock_info.points_count = 100
        mock_info.status = "green"
        mock_qdrant_client.return_value.get_collection = MagicMock(return_value=mock_info)

        info = service.get_collection_info("test_collection")
        assert info["vectors_count"] == 100
        assert info["status"] == "green"

    def test_get_collection_info_failure(self, service, mock_qdrant_client):
        """Test getting collection info failure."""
        mock_qdrant_client.return_value.get_collection = MagicMock(side_effect=Exception("Not found"))
        info = service.get_collection_info("nonexistent")
        assert info is None

    def test_health_check_healthy(self, service, mock_qdrant_client):
        """Test health check when healthy."""
        mock_qdrant_client.return_value.get_collections = MagicMock()
        result = service.health_check()
        assert result is True

    def test_health_check_unhealthy(self, service, mock_qdrant_client):
        """Test health check when unhealthy."""
        mock_qdrant_client.return_value.get_collections = MagicMock(side_effect=Exception("Connection refused"))
        result = service.health_check()
        assert result is False