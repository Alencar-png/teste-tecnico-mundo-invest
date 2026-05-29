from pydantic import BaseModel, EmailStr, Field

from schemas.client_schemas import ClientOut, GraphQLMutation


class WebhookCardUpdated(BaseModel):
    event_id: str = Field(..., min_length=1)
    card_id: str = Field(..., min_length=1)
    cliente_email: EmailStr
    timestamp: str


class WebhookResult(BaseModel):
    detail: str
    cliente: ClientOut | None = None
    pipefy_mutations: list[GraphQLMutation] = []
