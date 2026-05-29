"""ORM models (local database tables).

Column names are kept in Portuguese because they back the response contract
expected by the technical test; identifiers and docs are in English.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Client(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    tipo_solicitacao = Column(String, nullable=False)
    valor_patrimonio = Column(Numeric, nullable=False)
    status = Column(String, nullable=False)
    prioridade = Column(String, nullable=True)
    # Card id returned by Pipefy on creation (simulated here).
    pipefy_card_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class User(Base):
    """Internal operations user (JWT authentication)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="ADMIN")
    created_at = Column(DateTime, default=_utcnow)


class WebhookEvent(Base):
    """Record of already-processed webhook events — basis for idempotency."""

    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, nullable=False, unique=True, index=True)
    card_id = Column(String, nullable=True)
    cliente_email = Column(String, nullable=True)
    processed_at = Column(DateTime, default=_utcnow)
