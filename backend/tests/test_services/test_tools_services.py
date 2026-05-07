import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.agent_tools.tools.web_search import WebSearchService
from app.services.agent_tools.tools.url_fetch import URLFetchService
from app.services.agent_tools.tools.api_caller import APICallerService


class TestWebSearchService:
    """Tests for WebSearchService."""

    @pytest.fixture
    def service(self):
        return WebSearchService(api_key="test-key")

    @pytest.mark.asyncio
    async def test_search_success(self, service):
        """Test successful web search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "content": "Content 1"},
                {"title": "Result 2", "url": "https://example.com/2", "content": "Content 2"}
            ]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.search("test query", num_results=2)

        assert result["success"] is True
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "Result 1"

    @pytest.mark.asyncio
    async def test_search_failure(self, service):
        """Test search failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.search("test")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_and_fetch_success(self, service):
        """Test search and fetch combined."""
        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "results": [{"title": "Test", "url": "https://example.com", "content": "Content"}]
        }

        mock_fetch_response = MagicMock()
        mock_fetch_response.status_code = 200
        mock_fetch_response.text = "<html><body>Hello World</body></html>"
        mock_fetch_response.headers = {"content-type": "text/html"}

        with patch('httpx.AsyncClient') as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.post = AsyncMock(return_value=mock_search_response)
            instance.get = AsyncMock(return_value=mock_fetch_response)

            result = await service.search_and_fetch("test query")

        assert result["success"] is True
        assert "results" in result


class TestURLFetchService:
    """Tests for URLFetchService."""

    @pytest.fixture
    def service(self):
        return URLFetchService()

    @pytest.mark.asyncio
    async def test_fetch_success(self, service):
        """Test successful URL fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Hello</body></html>"
        mock_response.headers = {"content-type": "text/html"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await service.fetch("https://example.com")

        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert result["content"] == "<html><body>Hello</body></html>"

    @pytest.mark.asyncio
    async def test_fetch_truncation(self, service):
        """Test content truncation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "A" * 5000
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await service.fetch("https://example.com", max_length=100)

        assert result["truncated"] is True
        assert len(result["content"]) == 100

    @pytest.mark.asyncio
    async def test_fetch_failure(self, service):
        """Test fetch failure."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))
            result = await service.fetch("https://example.com")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fetch_and_clean(self, service):
        """Test fetch and clean HTML."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Hello</p></body></html>"
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await service.fetch_and_clean("https://example.com")

        assert result["success"] is True
        assert "<" not in result["content"]
        assert "Hello" in result["content"]


class TestAPICallerService:
    """Tests for APICallerService."""

    @pytest.fixture
    def service(self):
        return APICallerService()

    @pytest.mark.asyncio
    async def test_get_success(self, service):
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.headers = {"content-type": "application/json"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
            result = await service.get("https://api.example.com")

        assert result["success"] is True
        assert result["status"] == 200

    @pytest.mark.asyncio
    async def test_post_success(self, service):
        """Test successful POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 1}'
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
            result = await service.post("https://api.example.com", body={"name": "test"})

        assert result["success"] is True
        assert result["status"] == 201

    @pytest.mark.asyncio
    async def test_call_failure(self, service):
        """Test API call failure."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(side_effect=Exception("Timeout"))
            result = await service.call("https://api.example.com")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_success(self, service):
        """Test successful DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
            result = await service.delete("https://api.example.com/item/1")

        assert result["success"] is True
        assert result["status"] == 204

    @pytest.mark.asyncio
    async def test_call_with_headers(self, service):
        """Test API call with custom headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.headers = {}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
            result = await service.call(
                "https://api.example.com",
                headers={"Authorization": "Bearer token123"}
            )

        assert result["success"] is True
        call_args = mock_client.return_value.__aenter__.return_value.request.call_args
        headers = call_args.kwargs.get('headers', {})
        assert "Authorization" in headers