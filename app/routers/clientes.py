"""Router do Fluxo 1: criação de cliente."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.services import cliente_service
from app.services.pipefy_client import PipefyClient

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post(
    "", response_model=schemas.ClienteCreateResult, status_code=status.HTTP_201_CREATED
)
def criar_cliente(dados: schemas.ClienteCreate, db: Session = Depends(get_db)):
    try:
        cliente, mutations = cliente_service.criar_cliente(db, dados, PipefyClient())
    except cliente_service.ClienteJaExisteError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cliente com este e-mail já existe.",
        )
    return schemas.ClienteCreateResult(cliente=cliente, pipefy_mutations=mutations)


@router.get("", response_model=list[schemas.ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return cliente_service.listar_clientes(db)
