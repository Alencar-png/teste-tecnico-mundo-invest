"""Pipefy client (GraphQL).

This layer concentrates the queries/mutations in the EXACT format of Pipefy's
official GraphQL API. Instead of POSTing to https://api.pipefy.com/graphql, we
build the same payload (query + variables) and "simulate" the send, returning a
response in the same shape Pipefy would return.

Swapping the simulation for a real call is just replacing `_simulate_send` with
an authenticated POST — the mutation string and variables are already built.

Syntax based on the official documentation:
- createCard:      https://api-docs.pipefy.com/reference/mutations/createCard/
- updateCardField: https://api-docs.pipefy.com/reference/mutations/updateCardField/
"""
import logging
from decimal import Decimal

from app.config import PIPEFY_PIPE_ID

logger = logging.getLogger("pipefy")


# --------------------------------------------------------------------------- #
# MUTATIONS (official Pipefy syntax, parameterized with GraphQL variables)    #
# --------------------------------------------------------------------------- #

# createCard: creates a card in the pipe. `input` is of type CreateCardInput!,
# which accepts pipe_id, title and fields_attributes ([FieldValueInput] with
# field_id and field_value). Each field_id matches a field configured in the
# pipe's start form.
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

# updateCardField: updates ONE field of an existing card. `input` is of type
# UpdateCardFieldInput! (card_id, field_id, new_value). To update several fields
# we call the mutation once per field (see update_card).
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


class PipefyClient:
    def __init__(self, pipe_id: str = PIPEFY_PIPE_ID):
        self.pipe_id = pipe_id

    # ----- Flow 1: card creation ------------------------------------------ #
    def create_card(self, *, name: str, email: str, net_worth: Decimal) -> dict:
        """Builds and 'sends' the createCard mutation with the client data.

        Returns the created card and the exact GraphQL payload sent (query +
        variables) so the upper layer can expose it — single source of truth of
        what would go to Pipefy.
        """
        variables = {
            "input": {
                "pipe_id": self.pipe_id,
                "title": name,
                "fields_attributes": [
                    {"field_id": "cliente_nome", "field_value": name},
                    {"field_id": "cliente_email", "field_value": email},
                    {
                        "field_id": "valor_patrimonio",
                        "field_value": float(net_worth),
                    },
                ],
            }
        }
        response = self._simulate_send(CREATE_CARD_MUTATION, variables)
        return {
            "card": response["data"]["createCard"]["card"],
            "mutations": [
                {
                    "name": "createCard",
                    "query": CREATE_CARD_MUTATION,
                    "variables": variables,
                }
            ],
        }

    # ----- Flow 2: card update -------------------------------------------- #
    def update_card(self, *, card_id: str, status: str, priority: str) -> dict:
        """Updates status and priority calling updateCardField per field (DRY).

        Returns the results and the list of GraphQL payloads sent (one per field).
        """
        fields = {"status": status, "prioridade": priority}
        results = {}
        mutations = []
        for field_id, new_value in fields.items():
            variables = {
                "input": {
                    "card_id": card_id,
                    "field_id": field_id,
                    "new_value": new_value,
                }
            }
            response = self._simulate_send(UPDATE_CARD_FIELD_MUTATION, variables)
            results[field_id] = response["data"]["updateCardField"]["success"]
            mutations.append(
                {
                    "name": "updateCardField",
                    "query": UPDATE_CARD_FIELD_MUTATION,
                    "variables": variables,
                }
            )
        return {"results": results, "mutations": mutations}

    # ----- Transport simulation ------------------------------------------- #
    def _simulate_send(self, query: str, variables: dict) -> dict:
        """In place of the real POST to Pipefy, logs the payload and returns a
        response in the same shape as Pipefy's GraphQL API."""
        logger.info("Pipefy GraphQL >> query=%s variables=%s", query, variables)

        if "createCard" in query:
            return {
                "data": {
                    "createCard": {
                        "card": {
                            "id": "simulated-card-id",
                            "title": variables["input"]["title"],
                        },
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
