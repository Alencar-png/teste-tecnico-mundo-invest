"""Pydantic schemas: input validation and output serialization.

Field names follow the Portuguese contract mandated by the technical test;
class names and docs are in English.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Input ----------
class ClientCreate(BaseModel):
    cliente_nome: str = Field(..., min_length=1)
    cliente_email: EmailStr
    tipo_solicitacao: str = Field(..., min_length=1)
    valor_patrimonio: Decimal = Field(..., ge=0)


class WebhookCardUpdated(BaseModel):
    event_id: str = Field(..., min_length=1)
    card_id: str = Field(..., min_length=1)
    cliente_email: EmailStr
    timestamp: str


# ---------- Authentication ----------
class SecuritySchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Output ----------
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
    """Exact GraphQL payload that would be sent to Pipefy (for display)."""

    name: str
    query: str
    variables: dict


class ClientCreateResult(BaseModel):
    cliente: ClientOut
    pipefy_mutations: list[GraphQLMutation]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str


class WebhookResult(BaseModel):
    detail: str
    cliente: ClientOut | None = None
    pipefy_mutations: list[GraphQLMutation] = []
