import pytest
from unittest.mock import MagicMock, patch
from app.services.llm.chat import ChatService
from app.services.llm.embedding import EmbeddingService


class TestChatService:
    """Tests for ChatService (Ollama Cloud chat completions)."""

    def test_init_default(self):
        """Test service initialization with defaults."""
        with patch('app.services.llm.chat.settings') as mock_settings:
            mock_settings.OLLAMA_CLOUD_HOST = "http://default:11434"
            mock_settings.OLLAMA_API_KEY = "default-key"
            service = ChatService()
            assert service.base_url == "http://default:11434"
            assert service.api_key == "default-key"

    def test_init_custom(self):
        """Test service initialization with custom values."""
        service = ChatService(base_url="http://custom:11434", api_key="custom-key")
        assert service.base_url == "http://custom:11434"
        assert service.api_key == "custom-key"


class TestEmbeddingService:
    """Tests for EmbeddingService (Ollama embeddings)."""

    def test_init_default(self):
        """Test service initialization with defaults."""
        with patch('app.services.llm.embedding.settings') as mock_settings:
            mock_settings.OLLAMA_HOST = "http://default:11434"
            service = EmbeddingService()
            assert service.base_url == "http://default:11434"
            assert service.model == "nomic-embed-text"

    def test_init_custom(self):
        """Test service initialization with custom values."""
        service = EmbeddingService(base_url="http://custom:11434", model="other-model")
        assert service.base_url == "http://custom:11434"
        assert service.model == "other-model"