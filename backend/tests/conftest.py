import os
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

os.environ["DATABASE_URL"] = "postgresql://postgres:password@postgres:5432/tower_db"

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