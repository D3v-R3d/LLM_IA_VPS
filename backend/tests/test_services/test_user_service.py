import pytest
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User
from sqlalchemy.orm import Session


class TestUserService:
    def test_create_user(self, db_session: Session, sample_user_data):
        service = UserService()
        user_data = UserCreate(**sample_user_data)

        user = service.create(db_session, user_data)

        assert user.email == sample_user_data["email"]
        assert user.name == sample_user_data["name"]
        assert user.password_hash != sample_user_data["password"]

    def test_get_user_by_id(self, db_session: Session, sample_user_data):
        service = UserService()
        user_data = UserCreate(**sample_user_data)
        created = service.create(db_session, user_data)

        found = service.get_by_id(db_session, created.id)

        assert found is not None
        assert found.id == created.id

    def test_get_user_by_email(self, db_session: Session, sample_user_data):
        service = UserService()
        user_data = UserCreate(**sample_user_data)
        service.create(db_session, user_data)

        found = service.get_by_email(db_session, sample_user_data["email"])

        assert found is not None
        assert found.email == sample_user_data["email"]

    def test_authenticate_success(self, db_session: Session, sample_user_data):
        service = UserService()
        user_data = UserCreate(**sample_user_data)
        service.create(db_session, user_data)

        authenticated = service.authenticate(db_session, sample_user_data["email"], sample_user_data["password"])

        assert authenticated is not None
        assert authenticated.email == sample_user_data["email"]

    def test_authenticate_wrong_password(self, db_session: Session, sample_user_data):
        service = UserService()
        user_data = UserCreate(**sample_user_data)
        service.create(db_session, user_data)

        authenticated = service.authenticate(db_session, sample_user_data["email"], "wrongpassword")

        assert authenticated is None

    def test_update_user(self, db_session: Session, sample_user_data):
        service = UserService()
        user_data = UserCreate(**sample_user_data)
        created = service.create(db_session, user_data)

        update_data = UserUpdate(name="Updated Name")
        updated = service.update(db_session, created.id, update_data)

        assert updated is not None
        assert updated.name == "Updated Name"

    def test_delete_user(self, db_session: Session, sample_user_data):
        service = UserService()
        user_data = UserCreate(**sample_user_data)
        created = service.create(db_session, user_data)

        result = service.delete(db_session, created.id)

        assert result is True
        assert service.get_by_id(db_session, created.id) is None