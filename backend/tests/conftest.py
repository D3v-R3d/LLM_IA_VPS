import os

os.environ["DATABASE_URL"] = "postgresql://postgres:change_me_to_strong_password@postgres:5432/tower_db"
os.environ["JWT_SECRET"] = "test_secret_key_for_testing_only_do_not_use_in_production"
os.environ["OLLAMA_API_KEY"] = "test_ollama_api_key_for_testing"
os.environ["TELEGRAM_BOT_TOKEN"] = "test_telegram_token_for_testing"
os.environ["TELEGRAM_SECRET_TOKEN"] = "test_telegram_secret_for_testing"
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
os.environ["OLLAMA_CLOUD_HOST"] = "https://ollama.com"
os.environ["QDRANT_URL"] = "http://localhost:6333"

import pytest
import uuid
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.database import get_db
from app.main import app

test_engine = create_engine(
    os.environ["DATABASE_URL"],
    poolclass=NullPool,
    isolation_level="READ COMMITTED",
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False)


@pytest.fixture(scope="function")
def client():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()

test_engine = create_engine(
    os.environ["DATABASE_URL"],
    poolclass=NullPool,
    isolation_level="READ COMMITTED",
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False)


@pytest.fixture(scope="function")
def client():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.rollback()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, sample_user_data: dict) -> dict:
    """Create a user and return auth headers with JWT token."""
    register_response = client.post("/api/v1/users/register", json=sample_user_data)
    assert register_response.status_code == 201, f"Registration failed: {register_response.json()}"

    token = register_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_user_data():
    return {
        "email": f"test-{uuid.uuid4()}@example.com",
        "name": "Test User",
        "password": "securepassword123"
    }


@pytest.fixture(scope="function")
def sample_user_data():
    return {
        "email": f"test-{uuid.uuid4()}@example.com",
        "name": "Test User",
        "password": "securepassword123"
    }


@pytest.fixture(scope="function")
def sample_conversation_data():
    return {
        "title": "Test Conversation"
    }


@pytest.fixture(scope="function")
def sample_message_data():
    return {
        "role": "user",
        "content": "Hello, this is a test message"
    }


@pytest.fixture(scope="function")
def sample_document_data():
    return {
        "name": "test_document.txt",
        "type": "txt",
        "content_raw": "This is the content of the test document."
    }


def create_auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Helper to get auth headers for a user."""
    response = client.post("/api/v1/users/login", json={"email": email, "password": password})
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture(scope="function")
def sample_message_data():
    return {
        "role": "user",
        "content": "Hello, this is a test message"
    }


@pytest.fixture(scope="function")
def sample_document_data():
    return {
        "name": "test_document.txt",
        "type": "txt",
        "content_raw": "This is the content of the test document."
    }