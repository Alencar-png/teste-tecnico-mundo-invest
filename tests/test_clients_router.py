"""Teste obrigatório 1: criação de cliente com payload válido e persistência."""


def test_criar_cliente_valido_salva_no_banco(client, auth_headers):
    payload = {
        "cliente_nome": "João Silva",
        "cliente_email": "joao.silva@example.com",
        "tipo_solicitacao": "Atualização cadastral",
        "valor_patrimonio": 250000,
    }
    resp = client.post("/clientes", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    body = resp.json()
    cliente = body["cliente"]
    assert cliente["nome"] == "João Silva"
    assert cliente["status"] == "Aguardando Análise"
    assert cliente["prioridade"] is None
    assert cliente["pipefy_card_id"] == "simulated-card-id"

    # Expõe a mutation createCard exata.
    mutations = body["pipefy_mutations"]
    assert len(mutations) == 1
    assert mutations[0]["name"] == "createCard"
    assert "createCard(input: $input)" in mutations[0]["query"]

    # Persistiu: aparece na listagem e duplicar dá 409.
    listagem = client.get("/clientes", headers=auth_headers)
    assert listagem.status_code == 200
    assert any(c["email"] == "joao.silva@example.com" for c in listagem.json())
    dup = client.post("/clientes", json=payload, headers=auth_headers)
    assert dup.status_code == 409


def test_criar_cliente_sem_token_bloqueado(client):
    payload = {
        "cliente_nome": "Sem Auth",
        "cliente_email": "sem.auth@example.com",
        "tipo_solicitacao": "Atualização cadastral",
        "valor_patrimonio": 1000,
    }
    assert client.post("/clientes", json=payload).status_code in (401, 403)


def test_criar_cliente_email_invalido_retorna_422(client, auth_headers):
    payload = {
        "cliente_nome": "Maria",
        "cliente_email": "email-invalido",
        "tipo_solicitacao": "Atualização cadastral",
        "valor_patrimonio": 1000,
    }
    assert client.post("/clientes", json=payload, headers=auth_headers).status_code == 422


def test_criar_cliente_campo_obrigatorio_ausente_retorna_422(client, auth_headers):
    payload = {"cliente_email": "x@example.com", "valor_patrimonio": 1000}
    assert client.post("/clientes", json=payload, headers=auth_headers).status_code == 422
