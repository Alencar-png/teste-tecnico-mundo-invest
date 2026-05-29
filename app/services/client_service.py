"""Client business rules.

This is where the domain decisions live (initial status, priority calculation,
idempotency). Routers only translate HTTP <-> service; the repository only
persists. The external contract (field/status values) stays in Portuguese.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app import config, models, repository, schemas
from app.services.pipefy_client import PipefyClient


class ClientAlreadyExistsError(Exception):
    pass


class ClientNotFoundError(Exception):
    pass


class DuplicateEventError(Exception):
    pass


def _calculate_priority(net_worth: Decimal) -> str:
    """Net worth >= 200,000 => high priority; otherwise normal."""
    if net_worth >= config.HIGH_PRIORITY_THRESHOLD:
        return config.PRIORITY_HIGH
    return config.PRIORITY_NORMAL


def list_clients(db: Session) -> list[models.Client]:
    """Read for the dashboard/KPIs."""
    return repository.list_clients(db)


def create_client(
    db: Session, data: schemas.ClientCreate, pipefy: PipefyClient
) -> tuple[models.Client, list[dict]]:
    """Flow 1: persists the client as 'Aguardando Análise' and creates the card.

    Returns the client and the GraphQL mutations sent to Pipefy.
    """
    if repository.get_client_by_email(db, data.cliente_email):
        raise ClientAlreadyExistsError(data.cliente_email)

    client = repository.create_client(
        db,
        name=data.cliente_nome,
        email=data.cliente_email,
        request_type=data.tipo_solicitacao,
        net_worth=data.valor_patrimonio,
        status=config.STATUS_INITIAL,
    )

    # Pipefy mapping: create the matching card (createCard mutation).
    result = pipefy.create_card(
        name=client.nome,
        email=client.email,
        net_worth=client.valor_patrimonio,
    )
    client.pipefy_card_id = result["card"]["id"]
    db.commit()
    db.refresh(client)
    return client, result["mutations"]


def process_webhook(
    db: Session, data: schemas.WebhookCardUpdated, pipefy: PipefyClient
) -> tuple[models.Client, list[dict]]:
    """Flow 2: idempotency -> priority -> Pipefy update -> local database.

    Returns the client and the GraphQL mutations sent to Pipefy.
    """
    # 1. Idempotency: an already-seen event is not reprocessed.
    if repository.event_already_processed(db, data.event_id):
        raise DuplicateEventError(data.event_id)

    # 2. Locate the client and compute priority from the business rule.
    client = repository.get_client_by_email(db, data.cliente_email)
    if client is None:
        raise ClientNotFoundError(data.cliente_email)

    priority = _calculate_priority(client.valor_patrimonio)

    # 3. Pipefy mapping: send status + priority (updateCardField mutation).
    result = pipefy.update_card(
        card_id=data.card_id,
        status=config.STATUS_PROCESSED,
        priority=priority,
    )

    # 4. Update the local database and record the event (closes idempotency).
    repository.update_client(
        db, client, status=config.STATUS_PROCESSED, priority=priority
    )
    repository.register_event(
        db,
        event_id=data.event_id,
        card_id=data.card_id,
        client_email=data.cliente_email,
    )
    return client, result["mutations"]
