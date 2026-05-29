"""Camada de acesso a dados (repository).

Isola o SQLAlchemy das regras de negócio: o service nunca monta queries,
apenas chama estas funções.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app import models


def criar_cliente(
    db: Session,
    *,
    nome: str,
    email: str,
    tipo_solicitacao: str,
    valor_patrimonio: Decimal,
    status: str,
) -> models.Cliente:
    cliente = models.Cliente(
        nome=nome,
        email=email,
        tipo_solicitacao=tipo_solicitacao,
        valor_patrimonio=valor_patrimonio,
        status=status,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def buscar_cliente_por_email(db: Session, email: str) -> models.Cliente | None:
    return db.query(models.Cliente).filter(models.Cliente.email == email).first()


def listar_clientes(db: Session) -> list[models.Cliente]:
    return db.query(models.Cliente).order_by(models.Cliente.id.desc()).all()


def atualizar_cliente(
    db: Session, cliente: models.Cliente, *, status: str, prioridade: str
) -> models.Cliente:
    cliente.status = status
    cliente.prioridade = prioridade
    db.commit()
    db.refresh(cliente)
    return cliente


def evento_ja_processado(db: Session, event_id: str) -> bool:
    return (
        db.query(models.WebhookEvent)
        .filter(models.WebhookEvent.event_id == event_id)
        .first()
        is not None
    )


def registrar_evento(
    db: Session, *, event_id: str, card_id: str, cliente_email: str
) -> models.WebhookEvent:
    evento = models.WebhookEvent(
        event_id=event_id, card_id=card_id, cliente_email=cliente_email
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento
