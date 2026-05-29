"""Modelos ORM (tabelas do banco local)."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    tipo_solicitacao = Column(String, nullable=False)
    valor_patrimonio = Column(Numeric, nullable=False)
    status = Column(String, nullable=False)
    prioridade = Column(String, nullable=True)
    # ID do card retornado pelo Pipefy ao criar (aqui, simulado).
    pipefy_card_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class WebhookEvent(Base):
    """Registro de eventos de webhook já processados — base da idempotência."""

    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, nullable=False, unique=True, index=True)
    card_id = Column(String, nullable=True)
    cliente_email = Column(String, nullable=True)
    processed_at = Column(DateTime, default=_utcnow)
