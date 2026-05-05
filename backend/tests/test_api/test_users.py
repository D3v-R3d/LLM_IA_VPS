import pytest
from fastapi.testclient import TestClient


class TestUserEndpoints:
    def test_create_user(self, client: TestClient, sample_user_data):
        response = client.post("/api/v1/users/register", json=sample_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["name"] == sample_user_data["name"]
        assert "access_token" in data

    def test_create_user_duplicate_email(self, client: TestClient, sample_user_data):
        client.post("/api/v1/users/register", json=sample_user_data)
        response = client.post("/api/v1/users/register", json=sample_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_get_user(self, client: TestClient, sample_user_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        user_id = register_response.json()["user_id"]
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/v1/users/{user_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == sample_user_data["email"]

    def test_get_user_not_found(self, client: TestClient, sample_user_data):
        headers = client.post("/api/v1/users/register", json=sample_user_data).json()
        token = headers["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert response.status_code == 404

    def test_list_users(self, client: TestClient, sample_user_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_update_user(self, client: TestClient, sample_user_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        user_id = register_response.json()["user_id"]
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        update_data = {"name": "Updated Name"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_delete_user(self, client: TestClient, sample_user_data):
        register_response = client.post("/api/v1/users/register", json=sample_user_data)
        user_id = register_response.json()["user_id"]
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete(f"/api/v1/users/{user_id}", headers=headers)
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/users/{user_id}", headers=headers)
        assert get_response.status_code == 404