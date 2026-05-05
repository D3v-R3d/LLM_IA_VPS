import pytest
from fastapi.testclient import TestClient


class TestConversationEndpoints:
    def test_create_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_conversation_data["title"]
        assert data["user_id"] == user_id

    def test_get_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        create_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = create_response.json()["id"]

        response = client.get(f"/api/v1/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["id"] == conversation_id

    def test_get_conversation_not_found(self, client: TestClient):
        response = client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_list_user_conversations(self, client: TestClient, sample_user_data, sample_conversation_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        client.post("/api/v1/conversations", json=sample_conversation_data, params={"user_id": user_id})

        response = client.get(f"/api/v1/conversations/user/{user_id}")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_update_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        create_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = create_response.json()["id"]

        update_data = {"title": "Updated Title"}
        response = client.put(f"/api/v1/conversations/{conversation_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_delete_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        create_response = client.post(
            "/api/v1/conversations",
            json=sample_conversation_data,
            params={"user_id": user_id}
        )
        conversation_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/conversations/{conversation_id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/conversations/{conversation_id}")
        assert get_response.status_code == 404