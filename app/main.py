"""Ponto de entrada da aplicação FastAPI."""
import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app import config, repository
from app.database import Base, SessionLocal, engine
from app.routers import auth, clients, webhooks
from app.services import security_service

logging.basicConfig(level=logging.INFO)

# Create tables on startup (enough for SQLite/this test; in production we would
# use Alembic migrations).
Base.metadata.create_all(bind=engine)


def _seed_admin() -> None:
    """Ensures an admin user exists for login (idempotent)."""
    db = SessionLocal()
    try:
        if repository.get_user_by_email(db, config.DEFAULT_ADMIN_EMAIL) is None:
            repository.create_user(
                db,
                email=config.DEFAULT_ADMIN_EMAIL,
                hashed_password=security_service.hash_password(
                    config.DEFAULT_ADMIN_PASSWORD
                ),
                role="ADMIN",
            )
    finally:
        db.close()


_seed_admin()

app = FastAPI(title="Client Management & Pipefy Integration")

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(webhooks.router)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard():
    """Serve o dashboard (mesma origem da API: sem CORS, sem build)."""
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))
