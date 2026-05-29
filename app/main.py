"""Ponto de entrada da aplicação FastAPI."""
import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.database import Base, engine
from app.routers import clientes, webhooks

logging.basicConfig(level=logging.INFO)

# Cria as tabelas no startup (suficiente para SQLite/teste técnico; em produção
# usaríamos migrations com Alembic).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Client Management & Pipefy Integration")

app.include_router(clientes.router)
app.include_router(webhooks.router)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard():
    """Serve o dashboard (mesma origem da API: sem CORS, sem build)."""
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))
