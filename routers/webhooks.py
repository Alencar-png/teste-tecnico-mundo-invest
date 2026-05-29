from fastapi import APIRouter, Depends

from repositories.clients_repository import ClientsRepository, DuplicateEventError
from repositories.security_repository import SecurityRepository
from schemas.webhook_schemas import WebhookCardUpdated, WebhookResult

webhooks = APIRouter()


@webhooks.post(
    "/webhooks/pipefy/card-updated",
    response_model=WebhookResult,
    dependencies=[Depends(SecurityRepository.require_webhook_token)],
)
def card_updated(data: WebhookCardUpdated, repo: ClientsRepository = Depends()):
    try:
        client, mutations = repo.process_card_updated(data)
    except DuplicateEventError:
        # Idempotência: 200 com aviso — reentregas do webhook são esperadas.
        return WebhookResult(detail=f"Evento {data.event_id} já processado; ignorado.")
    return WebhookResult(
        detail="Webhook processado.", cliente=client, pipefy_mutations=mutations
    )
