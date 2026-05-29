from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uvicorn

from config import settings
from config.database import Base, SessionLocal, engine
from models.models import User, UserRole
from repositories.security_repository import SecurityRepository
from routers.security import security
from routers.clients import clients
from routers.webhooks import webhooks

# Conveniência de dev: garante as tabelas. Em produção, use `alembic upgrade head`.
Base.metadata.create_all(bind=engine)


def _seed_admin():
    """Garante um usuário admin para login (idempotente)."""
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == settings.DEFAULT_ADMIN_EMAIL).first():
            db.add(
                User(
                    name="Administrador",
                    email=settings.DEFAULT_ADMIN_EMAIL,
                    password=SecurityRepository.hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                )
            )
            db.commit()
    finally:
        db.close()


_seed_admin()

app = FastAPI(title="Client Management & Pipefy Integration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(security, tags=["security"])
app.include_router(clients, tags=["clientes"])
app.include_router(webhooks, tags=["webhooks"])

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard():
    """Serve o dashboard (mesma origem da API)."""
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
