import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.telegram.webhook import WebhookHandlerService, TelegramUpdate
from app.services.telegram.message_sender import MessageSenderService


class TestWebhookHandlerService:
    """Tests for WebhookHandlerService."""

    @pytest.fixture
    def service(self):
        return WebhookHandlerService()

    def test_verify_webhook_success(self, service):
        """Test webhook verification with correct token."""
        with patch('app.services.telegram.webhook.settings') as mock_settings:
            mock_settings.TELEGRAM_SECRET_TOKEN = "secret123"
            result = service.verify_webhook("secret123")
            assert result is True

    def test_verify_webhook_failure_wrong_token(self, service):
        """Test webhook verification with wrong token."""
        with patch('app.services.telegram.webhook.settings') as mock_settings:
            mock_settings.TELEGRAM_SECRET_TOKEN = "secret123"
            result = service.verify_webhook("wrongtoken")
            assert result is False

    def test_verify_webhook_failure_no_token(self, service):
        """Test webhook verification with no token provided."""
        with patch('app.services.telegram.webhook.settings') as mock_settings:
            mock_settings.TELEGRAM_SECRET_TOKEN = "secret123"
            result = service.verify_webhook(None)
            assert result is False

    def test_verify_webhook_failure_no_secret_configured(self, service):
        """Test webhook verification when no secret is configured."""
        with patch('app.services.telegram.webhook.settings') as mock_settings:
            mock_settings.TELEGRAM_SECRET_TOKEN = None
            result = service.verify_webhook("anytoken")
            assert result is False

    def test_parse_update_valid(self, service):
        """Test parsing valid update."""
        update_data = {
            "update_id": 12345,
            "message": {
                "text": "Hello",
                "chat": {"id": 67890}
            }
        }
        result = service.parse_update(update_data)
        assert result is not None
        assert result.update_id == 12345

    def test_parse_update_invalid(self, service):
        """Test parsing invalid update."""
        result = service.parse_update({"invalid": "data"})
        assert result is None

    def test_extract_message_text(self, service):
        """Test extracting message text from update."""
        update = TelegramUpdate(
            update_id=1,
            message={"text": "Hello World"}
        )
        result = service.extract_message_text(update)
        assert result == "Hello World"

    def test_extract_message_text_no_message(self, service):
        """Test extracting text when no message."""
        update = TelegramUpdate(update_id=1, message=None)
        result = service.extract_message_text(update)
        assert result is None

    def test_extract_chat_id(self, service):
        """Test extracting chat ID from update."""
        update = TelegramUpdate(
            update_id=1,
            message={"chat": {"id": 123456}}
        )
        result = service.extract_chat_id(update)
        assert result == 123456

    def test_extract_chat_id_no_chat(self, service):
        """Test extracting chat ID when no chat."""
        update = TelegramUpdate(update_id=1, message={})
        result = service.extract_chat_id(update)
        assert result is None

    def test_extract_command_valid(self, service):
        """Test extracting command from text."""
        command, args = service.extract_command("/start arg1 arg2")
        assert command == "start"
        assert args == "arg1 arg2"

    def test_extract_command_no_args(self, service):
        """Test extracting command without arguments."""
        command, args = service.extract_command("/help")
        assert command == "help"
        assert args is None

    def test_extract_command_lowercase(self, service):
        """Test command is lowercased."""
        command, args = service.extract_command("/START")
        assert command == "start"

    def test_extract_command_no_command(self, service):
        """Test extracting from non-command text."""
        command, args = service.extract_command("Hello world")
        assert command is None
        assert args is None

    def test_extract_command_empty(self, service):
        """Test extracting from empty text."""
        command, args = service.extract_command("")
        assert command is None


class TestMessageSenderService:
    """Tests for MessageSenderService."""

    @pytest.fixture
    def service(self):
        return MessageSenderService(bot_token="test-token")

    def test_init(self):
        """Test service initialization."""
        service = MessageSenderService(bot_token="my-token")
        assert service.bot_token == "my-token"
        assert "my-token" in service.api_url

    @pytest.mark.asyncio
    async def test_send_message_success(self, service):
        """Test successful message sending."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.send_message("12345", "Hello!")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_message_failure(self, service):
        """Test message sending failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.send_message("12345", "Hello!")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_info(self, service):
        """Test sending info notification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.send_notification("12345", "Title", "Message", "info")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_notification_success(self, service):
        """Test sending success notification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.send_notification("12345", "Done", "Task completed", "success")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_chat_action(self, service):
        """Test sending chat action."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.send_chat_action("12345", "typing")

        assert result is True

    @pytest.mark.asyncio
    async def test_get_me_success(self, service):
        """Test getting bot info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"id": 123, "is_bot": True, "first_name": "TestBot"}
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await service.get_me()

        assert result["is_bot"] is True
        assert result["first_name"] == "TestBot"

    @pytest.mark.asyncio
    async def test_get_me_failure(self, service):
        """Test getting bot info failure."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))
            result = await service.get_me()

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service):
        """Test health check when healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"is_bot": True}}

        with patch('httpx.AsyncClient') as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.get = AsyncMock(return_value=mock_response)
            result = await service.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, service):
        """Test health check when unhealthy."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Connection refused"))
            result = await service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_send_photo_success(self, service):
        """Test sending photo."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await service.send_photo("12345", "https://example.com/photo.jpg", caption="A photo")

        assert result is True