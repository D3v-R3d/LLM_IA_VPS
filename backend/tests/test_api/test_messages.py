import pytest
from fastapi.testclient import TestClient


class TestMessageEndpoints:
    def test_create_message(self, client: TestClient, sample_user_data, sample_conversation_data, sample_message_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        conv_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = conv_response.json()["id"]

        message_data = {**sample_message_data, "conversation_id": conversation_id}
        response = client.post(
            "/api/v1/messages",
            json=message_data,
            params={"user_id": user_id}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == sample_message_data["content"]
        assert data["role"] == sample_message_data["role"]

    def test_get_message(self, client: TestClient, sample_user_data, sample_conversation_data, sample_message_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        conv_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = conv_response.json()["id"]

        message_data = {**sample_message_data, "conversation_id": conversation_id}
        create_response = client.post(
            "/api/v1/messages",
            json=message_data,
            params={"user_id": user_id}
        )
        message_id = create_response.json()["id"]

        response = client.get(f"/api/v1/messages/{message_id}")
        assert response.status_code == 200
        assert response.json()["id"] == message_id

    def test_get_message_not_found(self, client: TestClient):
        response = client.get("/api/v1/messages/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_list_conversation_messages(self, client: TestClient, sample_user_data, sample_conversation_data, sample_message_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        conv_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = conv_response.json()["id"]

        message_data = {**sample_message_data, "conversation_id": conversation_id}
        client.post("/api/v1/messages", json=message_data, params={"user_id": user_id})

        response = client.get(f"/api/v1/messages/conversation/{conversation_id}")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_update_message(self, client: TestClient, sample_user_data, sample_conversation_data, sample_message_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        conv_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = conv_response.json()["id"]

        message_data = {**sample_message_data, "conversation_id": conversation_id}
        create_response = client.post(
            "/api/v1/messages",
            json=message_data,
            params={"user_id": user_id}
        )
        message_id = create_response.json()["id"]

        update_data = {"content": "Updated message content"}
        response = client.put(f"/api/v1/messages/{message_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["content"] == "Updated message content"

    def test_delete_message(self, client: TestClient, sample_user_data, sample_conversation_data, sample_message_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        conv_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = conv_response.json()["id"]

        message_data = {**sample_message_data, "conversation_id": conversation_id}
        create_response = client.post(
            "/api/v1/messages",
            json=message_data,
            params={"user_id": user_id}
        )
        message_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/messages/{message_id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/messages/{message_id}")
        assert get_response.status_code == 404