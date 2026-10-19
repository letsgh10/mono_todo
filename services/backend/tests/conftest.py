"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import create_access_token, hash_password
from app.db.models import User
from app.main import app


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine for each test."""
    engine = create_engine(
        "sqlite:///./test_todo.db",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a test database session for each test."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def test_user(test_db) -> User:
    """Create a regular test user in the database."""
    user = User(email="test@example.com", hashed_password=hash_password("password123"))
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin(test_db) -> User:
    """Create an admin test user in the database."""
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpass"),
        is_admin=True,
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


def _auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def _build_client(test_engine, user: User | None = None):
    """Yield a TestClient with session/AI overrides, optionally authenticated as `user`."""
    from app.api.routers.tasks import get_ai_service
    from app.db.session import get_session
    from app.services.ai_priority_service import MockAIPriorityService

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    def override_get_ai_service():
        return MockAIPriorityService()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_ai_service] = override_get_ai_service

    with TestClient(app) as test_client:
        if user is not None:
            test_client.headers.update(_auth_headers(user))
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def other_user(test_db) -> User:
    """Create a second regular user, unrelated to `test_user`."""
    user = User(email="other@example.com", hashed_password=hash_password("password123"))
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def client(test_engine, test_user):
    """Test client authenticated as a regular user."""
    yield from _build_client(test_engine, test_user)


@pytest.fixture(scope="function")
def other_client(test_engine, other_user):
    """Test client authenticated as `other_user`."""
    yield from _build_client(test_engine, other_user)


@pytest.fixture(scope="function")
def admin_client(test_engine, test_admin):
    """Test client authenticated as an admin user."""
    yield from _build_client(test_engine, test_admin)


@pytest.fixture(scope="function")
def unauth_client(test_engine):
    """Unauthenticated test client (for testing auth endpoints)."""
    yield from _build_client(test_engine)
