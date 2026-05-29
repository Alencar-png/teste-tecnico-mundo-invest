from fastapi import Depends

from models.models import WebhookEvent
from repositories.base_repository import BaseRepository, CRUDBase


class WebhookEventsRepository(CRUDBase):
    def __init__(self, base_repository: BaseRepository = Depends()):
        self.base_repository = base_repository

    @property
    def _entity(self):
        return WebhookEvent

    # ----- domínio: idempotência ----- #
    def already_processed(self, event_id: str) -> bool:
        return self.base_repository.db.query(self._entity).filter(
            self._entity.event_id == event_id
        ).first() is not None

    def register(self, *, event_id: str, card_id: str, client_email: str) -> WebhookEvent:
        event = WebhookEvent(
            event_id=event_id, card_id=card_id, cliente_email=client_email
        )
        return self.base_repository.create(event)

    # ----- CRUD (interface CRUDBase) ----- #
    def create(self, item):
        return self.base_repository.create(item)

    def find_one(self, item_id: int):
        return self.base_repository.find_one(self._entity, item_id)

    def find_all(self):
        return self.base_repository.find_all(self._entity)

    def update(self, item_id: int, current_object, item):
        return self.base_repository.update_one(self._entity, item_id, current_object, item)

    def delete(self, item_id: int):
        return self.base_repository.delete_one(self._entity, item_id)
