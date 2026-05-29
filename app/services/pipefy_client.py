"""Cliente Pipefy (GraphQL).

Esta camada concentra as queries/mutations no formato EXATO da API GraphQL
oficial do Pipefy. Em vez de fazer o POST real para https://api.pipefy.com/graphql,
nós montamos o mesmo payload (query + variables) e "simulamos" o envio, devolvendo
uma resposta no mesmo shape que o Pipefy retornaria.

Trocar a simulação por uma chamada real é só substituir `_simular_envio` por um
POST autenticado — a string da mutation e as variáveis já estão prontas.

Sintaxe baseada na documentação oficial:
- createCard:      https://api-docs.pipefy.com/reference/mutations/createCard/
- updateCardField: https://api-docs.pipefy.com/reference/mutations/updateCardField/
"""
import logging
from decimal import Decimal

from app.config import PIPEFY_PIPE_ID

logger = logging.getLogger("pipefy")


# --------------------------------------------------------------------------- #
# MUTATIONS (sintaxe oficial do Pipefy, parametrizada por variáveis GraphQL)  #
# --------------------------------------------------------------------------- #

# createCard: cria um card no pipe. `input` é do tipo CreateCardInput!, que
# aceita pipe_id, title e fields_attributes ([FieldValueInput] com field_id e
# field_value). Cada field_id corresponde a um campo configurado no formulário
# inicial do pipe.
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

# updateCardField: atualiza UM campo de um card existente. `input` é do tipo
# UpdateCardFieldInput! (card_id, field_id, new_value). Para atualizar vários
# campos chamamos a mutation uma vez por campo (ver atualizar_card).
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

    # ----- Fluxo 1: criação de card --------------------------------------- #
    def criar_card(
        self, *, nome: str, email: str, valor_patrimonio: Decimal
    ) -> dict:
        """Monta e 'envia' a mutation createCard com os dados do cliente.

        Devolve o card retornado e o payload GraphQL exato enviado (query +
        variables), para que a camada superior possa expô-lo — fonte única de
        verdade do que iria ao Pipefy.
        """
        variables = {
            "input": {
                "pipe_id": self.pipe_id,
                "title": nome,
                "fields_attributes": [
                    {"field_id": "cliente_nome", "field_value": nome},
                    {"field_id": "cliente_email", "field_value": email},
                    {
                        "field_id": "valor_patrimonio",
                        "field_value": float(valor_patrimonio),
                    },
                ],
            }
        }
        resposta = self._simular_envio(CREATE_CARD_MUTATION, variables)
        return {
            "card": resposta["data"]["createCard"]["card"],
            "mutations": [
                {
                    "name": "createCard",
                    "query": CREATE_CARD_MUTATION,
                    "variables": variables,
                }
            ],
        }

    # ----- Fluxo 2: atualização de card ----------------------------------- #
    def atualizar_card(self, *, card_id: str, status: str, prioridade: str) -> dict:
        """Atualiza status e prioridade chamando updateCardField por campo (DRY).

        Devolve os resultados e a lista de payloads GraphQL enviados (um por campo).
        """
        campos = {"status": status, "prioridade": prioridade}
        resultados = {}
        mutations = []
        for field_id, new_value in campos.items():
            variables = {
                "input": {
                    "card_id": card_id,
                    "field_id": field_id,
                    "new_value": new_value,
                }
            }
            resposta = self._simular_envio(UPDATE_CARD_FIELD_MUTATION, variables)
            resultados[field_id] = resposta["data"]["updateCardField"]["success"]
            mutations.append(
                {
                    "name": "updateCardField",
                    "query": UPDATE_CARD_FIELD_MUTATION,
                    "variables": variables,
                }
            )
        return {"results": resultados, "mutations": mutations}

    # ----- Simulação do transporte ---------------------------------------- #
    def _simular_envio(self, query: str, variables: dict) -> dict:
        """No lugar do POST real ao Pipefy, registra o payload e devolve um
        retorno no mesmo formato da API GraphQL do Pipefy."""
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
