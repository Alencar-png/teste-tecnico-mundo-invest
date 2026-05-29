"""Fixtures de teste: SQLite em memória isolado + TestClient autenticável."""
import os

# Força SQLite (sem MySQL) antes de qualquer import que toque config.database.
os.environ["TESTING"] = "1"

import bcrypt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from config.database import Base  # noqa: E402
from models.models import User, UserRole  # noqa: E402
from repositories.base_repository import get_db  # noqa: E402
from repositories.security_repository import WEBHOOK_TOKEN  # noqa: E402
from main import app  # noqa: E402

TEST_ADMIN = {"email": "admin@test.com", "password": "secret123"}


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Semeia o usuário admin de teste.
    db = TestingSessionLocal()
    db.add(
        User(
            name="Admin",
            email=TEST_ADMIN["email"],
            password=bcrypt.hashpw(
                TEST_ADMIN["password"].encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8"),
            role=UserRole.ADMIN,
        )
    )
    db.commit()
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
    resp = client.post("/login", json=TEST_ADMIN)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def webhook_headers():
    return {"X-Webhook-Token": WEBHOOK_TOKEN}
