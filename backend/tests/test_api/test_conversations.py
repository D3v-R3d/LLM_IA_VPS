import pytest
from fastapi.testclient import TestClient


class TestConversationEndpoints:
    def test_create_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/v1/conversations", json=sample_conversation_data, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_conversation_data["title"]

    def test_get_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = client.post("/api/v1/conversations", json=sample_conversation_data, headers=headers)
        conversation_id = create_response.json()["id"]

        response = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == conversation_id

    def test_get_conversation_not_found(self, client: TestClient, sample_user_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000", headers=headers)
        assert response.status_code == 404

    def test_list_user_conversations(self, client: TestClient, sample_user_data, sample_conversation_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/conversations", json=sample_conversation_data, headers=headers)

        response = client.get("/api/v1/conversations", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_update_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = client.post("/api/v1/conversations", json=sample_conversation_data, headers=headers)
        conversation_id = create_response.json()["id"]

        update_data = {"title": "Updated Title"}
        response = client.put(f"/api/v1/conversations/{conversation_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_delete_conversation(self, client: TestClient, sample_user_data, sample_conversation_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = client.post("/api/v1/conversations", json=sample_conversation_data, headers=headers)
        conversation_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/conversations/{conversation_id}", headers=headers)
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
        assert get_response.status_code == 404