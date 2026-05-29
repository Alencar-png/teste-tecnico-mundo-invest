"""Data access layer (repository).

Isolates SQLAlchemy from the business rules: services never build queries,
they only call these functions.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app import models


def create_client(
    db: Session,
    *,
    name: str,
    email: str,
    request_type: str,
    net_worth: Decimal,
    status: str,
) -> models.Client:
    client = models.Client(
        nome=name,
        email=email,
        tipo_solicitacao=request_type,
        valor_patrimonio=net_worth,
        status=status,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_client_by_email(db: Session, email: str) -> models.Client | None:
    return db.query(models.Client).filter(models.Client.email == email).first()


def list_clients(db: Session) -> list[models.Client]:
    return db.query(models.Client).order_by(models.Client.id.desc()).all()


def update_client(
    db: Session, client: models.Client, *, status: str, priority: str
) -> models.Client:
    client.status = status
    client.prioridade = priority
    db.commit()
    db.refresh(client)
    return client


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(
    db: Session, *, email: str, hashed_password: str, role: str = "ADMIN"
) -> models.User:
    user = models.User(email=email, hashed_password=hashed_password, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def event_already_processed(db: Session, event_id: str) -> bool:
    return (
        db.query(models.WebhookEvent)
        .filter(models.WebhookEvent.event_id == event_id)
        .first()
        is not None
    )


def register_event(
    db: Session, *, event_id: str, card_id: str, client_email: str
) -> models.WebhookEvent:
    event = models.WebhookEvent(
        event_id=event_id, card_id=card_id, cliente_email=client_email
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
