from decimal import Decimal
from http import HTTPStatus

from fastapi import Depends, HTTPException

from config import settings
from models.models import Client
from repositories.base_repository import BaseRepository, CRUDBase
from repositories.pipefy_repository import PipefyRepository
from repositories.webhook_events_repository import WebhookEventsRepository


class DuplicateEventError(Exception):
    """Evento de webhook já processado (idempotência)."""


class ClientsRepository(CRUDBase):
    def __init__(
        self,
        base_repository: BaseRepository = Depends(),
        pipefy: PipefyRepository = Depends(),
        webhook_events: WebhookEventsRepository = Depends(),
    ):
        self.base_repository = base_repository
        self.pipefy = pipefy
        self.webhook_events = webhook_events

    @property
    def _entity(self):
        return Client

    def find_by_email(self, email: str):
        return self.base_repository.db.query(self._entity).filter(
            self._entity.email == email
        ).first()

    # ----- Fluxo 1: criação de cliente + card ----- #
    def create(self, data):
        if self.find_by_email(data.cliente_email):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Cliente com este e-mail já existe.",
            )

        client = Client(
            nome=data.cliente_nome,
            email=data.cliente_email,
            tipo_solicitacao=data.tipo_solicitacao,
            valor_patrimonio=data.valor_patrimonio,
            status=settings.STATUS_INITIAL,
        )
        self.base_repository.create(client)

        # Mapeamento Pipefy: createCard.
        result = self.pipefy.create_card(
            name=client.nome, email=client.email, net_worth=client.valor_patrimonio
        )
        client.pipefy_card_id = result["card"]["id"]
        self.base_repository.db.commit()
        self.base_repository.db.refresh(client)
        return client, result["mutations"]

    # ----- Fluxo 2: webhook (idempotência + prioridade + update) ----- #
    def process_card_updated(self, data):
        if self.webhook_events.already_processed(data.event_id):
            raise DuplicateEventError(data.event_id)

        client = self.find_by_email(data.cliente_email)
        if client is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Cliente não encontrado para o e-mail informado.",
            )

        priority = self._priority(client.valor_patrimonio)

        # Mapeamento Pipefy: updateCardField (status + prioridade).
        result = self.pipefy.update_card(
            card_id=data.card_id, status=settings.STATUS_PROCESSED, priority=priority
        )

        client.status = settings.STATUS_PROCESSED
        client.prioridade = priority
        self.base_repository.db.commit()
        self.base_repository.db.refresh(client)

        self.webhook_events.register(
            event_id=data.event_id, card_id=data.card_id, client_email=data.cliente_email
        )
        return client, result["mutations"]

    @staticmethod
    def _priority(net_worth: Decimal) -> str:
        if net_worth >= settings.HIGH_PRIORITY_THRESHOLD:
            return settings.PRIORITY_HIGH
        return settings.PRIORITY_NORMAL

    # ----- CRUD (interface CRUDBase) ----- #
    def find_one(self, item_id: int):
        return self.base_repository.find_one(self._entity, item_id)

    def find_all(self):
        return self.base_repository.find_all(self._entity)

    def update(self, item_id: int, current_object, item):
        return self.base_repository.update_one(self._entity, item_id, current_object, item)

    def delete(self, item_id: int):
        return self.base_repository.delete_one(self._entity, item_id)
