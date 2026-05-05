import pytest
from fastapi.testclient import TestClient


class TestDocumentEndpoints:
    def test_create_document(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        response = client.post(
            "/api/v1/documents",
            json=sample_document_data,
            params={"user_id": user_id}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_document_data["name"]
        assert data["type"] == sample_document_data["type"]
        assert data["user_id"] == user_id

    def test_get_document(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        create_response = client.post(
            "/api/v1/documents",
            json=sample_document_data,
            params={"user_id": user_id}
        )
        document_id = create_response.json()["id"]

        response = client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == 200
        assert response.json()["id"] == document_id

    def test_get_document_not_found(self, client: TestClient):
        response = client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_list_user_documents(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        client.post("/api/v1/documents", json=sample_document_data, params={"user_id": user_id})

        response = client.get(f"/api/v1/documents/user/{user_id}")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_list_documents(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        client.post("/api/v1/documents", json=sample_document_data, params={"user_id": user_id})

        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_update_document(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        create_response = client.post(
            "/api/v1/documents",
            json=sample_document_data,
            params={"user_id": user_id}
        )
        document_id = create_response.json()["id"]

        update_data = {"name": "Updated Document Name"}
        response = client.put(f"/api/v1/documents/{document_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Document Name"

    def test_delete_document(self, client: TestClient, sample_user_data, sample_document_data):
        user_response = client.post("/api/v1/users", json=sample_user_data)
        user_id = user_response.json()["id"]

        create_response = client.post(
            "/api/v1/documents",
            json=sample_document_data,
            params={"user_id": user_id}
        )
        document_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/documents/{document_id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/documents/{document_id}")
        assert get_response.status_code == 404