import pytest
from unittest.mock import patch, MagicMock
from app.services.context_service import ContextService, CONTEXT_CONFIG


class MockMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content


class TestContextService:
    def test_get_token_count_empty(self):
        service = ContextService()
        messages = []

        token_count = service.get_token_count(messages)

        assert token_count == 0

    def test_get_token_count_basic(self):
        service = ContextService()
        messages = [
            MockMessage("user", "Hello world"),
            MockMessage("assistant", "Hi there!")
        ]

        token_count = service.get_token_count(messages)

        assert token_count == (len("Hello world") + len("Hi there!")) // 4

    def test_get_token_count_with_empty_content(self):
        service = ContextService()
        messages = [
            MockMessage("user", "Hello world"),
            MockMessage("assistant", ""),
            MockMessage("user", "Test")
        ]

        token_count = service.get_token_count(messages)

        expected = (len("Hello world") + len("Test")) // 4
        assert token_count == expected

    def test_get_token_count_none_content(self):
        service = ContextService()
        messages = [
            MockMessage("user", "Hello world"),
            MockMessage("assistant", None),
        ]

        token_count = service.get_token_count(messages)

        assert token_count == len("Hello world") // 4

    def test_should_compress_false_under_threshold(self):
        service = ContextService()
        messages = [
            MockMessage("user", "x" * 100)
        ]

        conversation = MagicMock()
        conversation.messages = messages

        result = service.should_compress(conversation)

        assert result is False

    def test_should_compress_true_over_threshold(self):
        service = ContextService()
        messages = [
            MockMessage("user", "x" * 10000)
        ]

        conversation = MagicMock()
        conversation.messages = messages

        result = service.should_compress(conversation)

        assert result is True

    def test_should_compress_empty_messages(self):
        service = ContextService()
        conversation = MagicMock()
        conversation.messages = []

        result = service.should_compress(conversation)

        assert result is False

    def test_compress_conversation_under_keep_threshold(self):
        service = ContextService()
        messages = [MockMessage("user", f"Message {i}") for i in range(5)]

        conversation = MagicMock()
        conversation.messages = messages
        conversation.id = "conv-id"
        conversation.user_id = "user-id"

        result = service.compress_conversation(MagicMock(), conversation)

        assert result is None

    def test_compress_conversation_no_content(self):
        service = ContextService()
        messages = [MockMessage("user", "") for i in range(20)]

        conversation = MagicMock()
        conversation.messages = messages
        conversation.id = "conv-id"
        conversation.user_id = "user-id"

        result = service.compress_conversation(MagicMock(), conversation)

        assert result is None

    def test_get_context_info(self):
        service = ContextService()
        messages = [MockMessage("user", "x" * 1000) for _ in range(10)]

        conversation = MagicMock()
        conversation.messages = messages

        info = service.get_context_info(conversation)

        assert "tokens" in info
        assert "messages" in info
        assert "should_compress" in info
        assert "max_tokens" in info
        assert "keep_last" in info
        assert info["messages"] == 10