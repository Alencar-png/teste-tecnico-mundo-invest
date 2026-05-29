"""Schemas Pydantic: validação de entrada e serialização de saída."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Entrada ----------
class ClienteCreate(BaseModel):
    cliente_nome: str = Field(..., min_length=1)
    cliente_email: EmailStr
    tipo_solicitacao: str = Field(..., min_length=1)
    valor_patrimonio: Decimal = Field(..., ge=0)


class WebhookCardUpdated(BaseModel):
    event_id: str = Field(..., min_length=1)
    card_id: str = Field(..., min_length=1)
    cliente_email: EmailStr
    timestamp: str


# ---------- Saída ----------
class ClienteOut(BaseModel):
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


class ClienteCreateResult(BaseModel):
    cliente: ClienteOut
    pipefy_mutations: list[GraphQLMutation]


class WebhookResult(BaseModel):
    detail: str
    cliente: ClienteOut | None = None
    pipefy_mutations: list[GraphQLMutation] = []
