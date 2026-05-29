"""Pipefy repository (GraphQL).

Concentra as queries/mutations no formato EXATO da API GraphQL oficial do Pipefy.
Em vez do POST real para https://api.pipefy.com/graphql, montamos o mesmo payload
(query + variables) e simulamos o envio (_simulate_send), devolvendo a resposta no
mesmo shape. Trocar pela chamada real é só substituir o transporte.

Sintaxe baseada na documentação oficial:
- createCard:      https://api-docs.pipefy.com/reference/mutations/createCard/
- updateCardField: https://api-docs.pipefy.com/reference/mutations/updateCardField/
"""
import logging
import os
from decimal import Decimal

logger = logging.getLogger("pipefy")


# createCard: input do tipo CreateCardInput! (pipe_id, title, fields_attributes
# -> lista de FieldValueInput com field_id/field_value).
CREATE_CARD_MUTATION = """
mutation CreateCard($input: CreateCardInput!) {
  createCard(input: $input) {
    card {
      id
      title
    }
    clientMutationId
  }
}
""".strip()

# updateCardField: input do tipo UpdateCardFieldInput! (card_id, field_id, new_value).
UPDATE_CARD_FIELD_MUTATION = """
mutation UpdateCardField($input: UpdateCardFieldInput!) {
  updateCardField(input: $input) {
    card {
      id
      title
    }
    success
    clientMutationId
  }
}
""".strip()


class PipefyRepository:
    def __init__(self):
        self.pipe_id = os.getenv("PIPEFY_PIPE_ID", "301613")

    def create_card(self, *, name: str, email: str, net_worth: Decimal) -> dict:
        """Monta e simula a mutation createCard; devolve o card e o payload enviado."""
        variables = {
            "input": {
                "pipe_id": self.pipe_id,
                "title": name,
                "fields_attributes": [
                    {"field_id": "cliente_nome", "field_value": name},
                    {"field_id": "cliente_email", "field_value": email},
                    {"field_id": "valor_patrimonio", "field_value": float(net_worth)},
                ],
            }
        }
        response = self._simulate_send(CREATE_CARD_MUTATION, variables)
        return {
            "card": response["data"]["createCard"]["card"],
            "mutations": [
                {"name": "createCard", "query": CREATE_CARD_MUTATION, "variables": variables}
            ],
        }

    def update_card(self, *, card_id: str, status: str, priority: str) -> dict:
        """Atualiza status e prioridade chamando updateCardField por campo (DRY)."""
        fields = {"status": status, "prioridade": priority}
        results = {}
        mutations = []
        for field_id, new_value in fields.items():
            variables = {
                "input": {"card_id": card_id, "field_id": field_id, "new_value": new_value}
            }
            response = self._simulate_send(UPDATE_CARD_FIELD_MUTATION, variables)
            results[field_id] = response["data"]["updateCardField"]["success"]
            mutations.append(
                {"name": "updateCardField", "query": UPDATE_CARD_FIELD_MUTATION, "variables": variables}
            )
        return {"results": results, "mutations": mutations}

    def _simulate_send(self, query: str, variables: dict) -> dict:
        """No lugar do POST real ao Pipefy, loga o payload e devolve a resposta
        no mesmo shape da API GraphQL do Pipefy."""
        logger.info("Pipefy GraphQL >> query=%s variables=%s", query, variables)
        if "createCard" in query:
            return {
                "data": {
                    "createCard": {
                        "card": {"id": "simulated-card-id", "title": variables["input"]["title"]},
                        "clientMutationId": None,
                    }
                }
            }
        return {
            "data": {
                "updateCardField": {
                    "card": {"id": variables["input"]["card_id"], "title": ""},
                    "success": True,
                    "clientMutationId": None,
                }
            }
        }
