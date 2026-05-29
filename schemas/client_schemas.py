from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Entrada ----------
class ClientCreate(BaseModel):
    cliente_nome: str = Field(..., min_length=1)
    cliente_email: EmailStr
    tipo_solicitacao: str = Field(..., min_length=1)
    valor_patrimonio: Decimal = Field(..., ge=0)


# ---------- Saída ----------
class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    tipo_solicitacao: str
    valor_patrimonio: Decimal
    status: str
    prioridade: str | None = None
    pipefy_card_id: str | None = None


class GraphQLMutation(BaseModel):
    """Payload GraphQL exato que seria enviado ao Pipefy (para exibição)."""

    name: str
    query: str
    variables: dict


class ClientCreateResult(BaseModel):
    cliente: ClientOut
    pipefy_mutations: list[GraphQLMutation]
