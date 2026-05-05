import pytest
from fastapi.testclient import TestClient


class TestUserEndpoints:
    def test_create_user(self, client: TestClient, sample_user_data):
        response = client.post("/api/v1/users", json=sample_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["name"] == sample_user_data["name"]
        assert "id" in data

    def test_create_user_duplicate_email(self, client: TestClient, sample_user_data):
        client.post("/api/v1/users", json=sample_user_data)
        response = client.post("/api/v1/users", json=sample_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_get_user(self, client: TestClient, sample_user_data):
        create_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = create_response.json()["id"]

        response = client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["email"] == sample_user_data["email"]

    def test_get_user_not_found(self, client: TestClient):
        response = client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_list_users(self, client: TestClient, sample_user_data):
        client.post("/api/v1/users", json=sample_user_data)
        response = client.get("/api/v1/users")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_update_user(self, client: TestClient, sample_user_data):
        create_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = create_response.json()["id"]

        update_data = {"name": "Updated Name"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_delete_user(self, client: TestClient, sample_user_data):
        create_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/users/{user_id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == 404