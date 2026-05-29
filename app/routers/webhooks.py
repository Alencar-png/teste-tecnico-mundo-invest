"""Flow 2 router: Pipefy card-updated webhook."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services import client_service
from app.services.pipefy_client import PipefyClient
from app.services.security_service import require_webhook_token

router = APIRouter(prefix="/webhooks/pipefy", tags=["webhooks"])


@router.post(
    "/card-updated",
    response_model=schemas.WebhookResult,
    dependencies=[Depends(require_webhook_token)],
)
def card_updated(data: schemas.WebhookCardUpdated, db: Session = Depends(get_db)):
    try:
        client, mutations = client_service.process_webhook(db, data, PipefyClient())
    except client_service.DuplicateEventError:
        # Idempotency: 200 with a notice — webhook re-deliveries are expected.
        return schemas.WebhookResult(
            detail=f"Evento {data.event_id} já processado; ignorado."
        )
    except client_service.ClientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado para o e-mail informado.",
        )
    return schemas.WebhookResult(
        detail="Webhook processado.", cliente=client, pipefy_mutations=mutations
    )
