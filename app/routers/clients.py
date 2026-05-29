"""Flow 1 router: client creation and listing.

Route path stays /clientes (test contract); code is in English.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import client_service
from app.services.pipefy_client import PipefyClient
from app.services.security_service import get_current_user

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post(
    "", response_model=schemas.ClientCreateResult, status_code=status.HTTP_201_CREATED
)
def create_client(
    data: schemas.ClientCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    try:
        client, mutations = client_service.create_client(db, data, PipefyClient())
    except client_service.ClientAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cliente com este e-mail já existe.",
        )
    return schemas.ClientCreateResult(cliente=client, pipefy_mutations=mutations)


@router.get("", response_model=list[schemas.ClientOut])
def list_clients(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return client_service.list_clients(db)
