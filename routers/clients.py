from fastapi import APIRouter, Depends, status

from repositories.clients_repository import ClientsRepository
from repositories.security_repository import SecurityRepository
from schemas.client_schemas import ClientCreateResult, ClientCreate, ClientOut

clients = APIRouter()


@clients.post("/clientes", response_model=ClientCreateResult, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate,
    repo: ClientsRepository = Depends(),
    current_user: dict = Depends(SecurityRepository.get_current_user),
):
    client, mutations = repo.create(data)
    return ClientCreateResult(cliente=client, pipefy_mutations=mutations)


@clients.get("/clientes", response_model=list[ClientOut])
def list_clients(
    repo: ClientsRepository = Depends(),
    current_user: dict = Depends(SecurityRepository.get_current_user),
):
    return repo.find_all()
