import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

os.environ["TELEGRAM_BOT_TOKEN"] = "test-bot-token"
os.environ["TELEGRAM_SECRET_TOKEN"] = "test-secret"
os.environ["JWT_SECRET"] = "test-jwt-secret"

sys.modules["app.models.database"] = MagicMock()
sys.modules["app.models"] = MagicMock()
sys.modules["app.models.user"] = MagicMock()
sys.modules["app.models.conversation"] = MagicMock()
sys.modules["app.models.message"] = MagicMock()
sys.modules["app.models.document"] = MagicMock()
sys.modules["app.models.user_model_prefs"] = MagicMock()
sys.modules["sqlalchemy.orm"] = MagicMock()

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_telegram():
    with patch("app.api.v1.telegram.telegram_service") as mock:
        yield mock


class TestWebhookPostEndpoint:
    WEBHOOK_URL = "/api/v1/telegram/webhook"

    def test_webhook_valid_token(self, client, mock_telegram):
        mock_telegram.verify_webhook.return_value = True

        response = client.post(
            self.WEBHOOK_URL,
            json={"update_id": 1, "message": {"text": "/help", "chat": {"id": 999}}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "valid-token"},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_webhook_invalid_token(self, client, mock_telegram):
        mock_telegram.verify_webhook.return_value = False

        response = client.post(
            self.WEBHOOK_URL,
            json={"update_id": 1, "message": {"text": "/help", "chat": {"id": 999}}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-token"},
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid secret token"}

    def test_webhook_missing_token_header(self, client, mock_telegram):
        mock_telegram.verify_webhook.return_value = False

        response = client.post(
            self.WEBHOOK_URL,
            json={"update_id": 1, "message": {"text": "/help", "chat": {"id": 999}}},
        )

        assert response.status_code == 403

    def test_webhook_verify_called_with_header(self, client, mock_telegram):
        mock_telegram.verify_webhook.return_value = True

        client.post(
            self.WEBHOOK_URL,
            json={"update_id": 1, "message": {"text": "hello", "chat": {"id": 999}}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "my-secret"},
        )

        mock_telegram.verify_webhook.assert_called_once_with("my-secret")


class TestWebhookGetEndpoint:
    def test_webhook_get_returns_ok(self, client):
        response = client.get("/api/v1/telegram/webhook")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestWebhookInfoEndpoint:
    def test_webhook_info_success(self, client, mock_telegram):
        mock_info = {
            "url": "https://example.com/webhook",
            "has_custom_certificate": False,
            "pending_update_count": 0,
        }
        mock_telegram.get_webhook_info = AsyncMock(return_value=mock_info)

        response = client.get("/api/v1/telegram/webhook-info")
        assert response.status_code == 200
        assert response.json() == mock_info

    def test_webhook_info_failure_returns_500(self, client, mock_telegram):
        mock_telegram.get_webhook_info = AsyncMock(return_value=None)

        response = client.get("/api/v1/telegram/webhook-info")
        assert response.status_code == 500


class TestWebhookDeleteEndpoint:
    def test_delete_webhook_success(self, client, mock_telegram):
        mock_telegram.delete_webhook = AsyncMock(return_value=True)

        response = client.delete("/api/v1/telegram/webhook")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_delete_webhook_failure_returns_500(self, client, mock_telegram):
        mock_telegram.delete_webhook = AsyncMock(return_value=False)

        response = client.delete("/api/v1/telegram/webhook")
        assert response.status_code == 500


class TestWebhookSetupEndpoint:
    def test_setup_webhook_success(self, client, mock_telegram):
        mock_telegram.set_webhook = AsyncMock(return_value=True)

        response = client.post(
            "/api/v1/telegram/setup-webhook?url=https://example.com/webhook"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["webhook_url"] == "https://example.com/webhook"

    def test_setup_webhook_failure_returns_500(self, client, mock_telegram):
        mock_telegram.set_webhook = AsyncMock(return_value=False)

        response = client.post(
            "/api/v1/telegram/setup-webhook?url=https://example.com/webhook"
        )
        assert response.status_code == 500


class TestWebhookBackgroundTask:
    def test_background_task_is_created(self, client, mock_telegram):
        mock_telegram.verify_webhook.return_value = True

        with patch("app.api.v1.telegram.get_message_pipeline") as mock_get_pipeline:
            response = client.post(
                "/api/v1/telegram/webhook",
                json={"update_id": 42, "message": {"text": "hello", "chat": {"id": 1}}},
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid"},
            )

            assert response.status_code == 200
            mock_get_pipeline.assert_called_once()
