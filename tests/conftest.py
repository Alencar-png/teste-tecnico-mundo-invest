"""Fixtures de teste: banco SQLite isolado em memória + TestClient."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, repository
from app.database import Base, get_db
from app.main import app
from app.services import security_service

TEST_USER = {"email": "admin@test.com", "password": "secret123"}


@pytest.fixture
def client():
    # StaticPool + memória compartilhada: todas as conexões enxergam a mesma base.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed the test user for authentication.
    db = TestingSessionLocal()
    repository.create_user(
        db,
        email=TEST_USER["email"],
        hashed_password=security_service.hash_password(TEST_USER["password"]),
    )
    db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Faz login e devolve o header Authorization Bearer."""
    resp = client.post("/login", json=TEST_USER)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def webhook_headers():
    """Header com o segredo do webhook."""
    return {"X-Webhook-Token": config.WEBHOOK_TOKEN}
