"""Router do Fluxo 2: webhook de card atualizado."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services import cliente_service
from app.services.pipefy_client import PipefyClient

router = APIRouter(prefix="/webhooks/pipefy", tags=["webhooks"])


@router.post("/card-updated", response_model=schemas.WebhookResult)
def card_updated(dados: schemas.WebhookCardUpdated, db: Session = Depends(get_db)):
    try:
        cliente, mutations = cliente_service.processar_webhook(db, dados, PipefyClient())
    except cliente_service.EventoDuplicadoError:
        # Idempotência: 200 com aviso — reentregas do webhook são esperadas.
        return schemas.WebhookResult(
            detail=f"Evento {dados.event_id} já processado; ignorado."
        )
    except cliente_service.ClienteNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado para o e-mail informado.",
        )
    return schemas.WebhookResult(
        detail="Webhook processado.", cliente=cliente, pipefy_mutations=mutations
    )
