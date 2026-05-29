"""Testes obrigatórios 2 e 3: regra de prioridade e idempotência do webhook."""
import pytest


def _criar_cliente(client, auth_headers, email, valor):
    return client.post(
        "/clientes",
        json={
            "cliente_nome": "Cliente Teste",
            "cliente_email": email,
            "tipo_solicitacao": "Atualização cadastral",
            "valor_patrimonio": valor,
        },
        headers=auth_headers,
    )


@pytest.mark.parametrize(
    "valor,prioridade_esperada",
    [
        (250000, "prioridade_alta"),    # >= 200.000
        (200000, "prioridade_alta"),    # limiar (>=)
        (199999, "prioridade_normal"),  # < 200.000
        (50000, "prioridade_normal"),
    ],
)
def test_webhook_aplica_regra_de_prioridade(
    client, auth_headers, webhook_headers, valor, prioridade_esperada
):
    email = f"cliente{valor}@example.com"
    _criar_cliente(client, auth_headers, email, valor)

    resp = client.post(
        "/webhooks/pipefy/card-updated",
        json={
            "event_id": f"evt_{valor}",
            "card_id": "card_456",
            "cliente_email": email,
            "timestamp": "2026-05-18T12:00:00Z",
        },
        headers=webhook_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    cliente = body["cliente"]
    assert cliente["status"] == "Processado"
    assert cliente["prioridade"] == prioridade_esperada

    mutations = body["pipefy_mutations"]
    assert [m["name"] for m in mutations] == ["updateCardField", "updateCardField"]
    enviados = {m["variables"]["input"]["new_value"] for m in mutations}
    assert enviados == {"Processado", prioridade_esperada}


def test_webhook_event_id_duplicado_e_bloqueado(client, auth_headers, webhook_headers):
    email = "joao.silva@example.com"
    _criar_cliente(client, auth_headers, email, 250000)
    payload = {
        "event_id": "evt_123",
        "card_id": "card_456",
        "cliente_email": email,
        "timestamp": "2026-05-18T12:00:00Z",
    }

    primeira = client.post(
        "/webhooks/pipefy/card-updated", json=payload, headers=webhook_headers
    )
    assert primeira.status_code == 200
    assert primeira.json()["cliente"]["status"] == "Processado"

    segunda = client.post(
        "/webhooks/pipefy/card-updated", json=payload, headers=webhook_headers
    )
    assert segunda.status_code == 200
    assert "já processado" in segunda.json()["detail"]
    assert segunda.json()["cliente"] is None


def test_webhook_token_invalido_retorna_401(client):
    resp = client.post(
        "/webhooks/pipefy/card-updated",
        json={
            "event_id": "evt_x",
            "card_id": "card_456",
            "cliente_email": "x@example.com",
            "timestamp": "2026-05-18T12:00:00Z",
        },
        headers={"X-Webhook-Token": "errado"},
    )
    assert resp.status_code == 401


def test_webhook_cliente_inexistente_retorna_404(client, webhook_headers):
    resp = client.post(
        "/webhooks/pipefy/card-updated",
        json={
            "event_id": "evt_999",
            "card_id": "card_456",
            "cliente_email": "naoexiste@example.com",
            "timestamp": "2026-05-18T12:00:00Z",
        },
        headers=webhook_headers,
    )
    assert resp.status_code == 404
