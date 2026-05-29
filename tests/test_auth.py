"""Testes de autenticação (login, token e proteção de rotas)."""
from tests.conftest import TEST_USER


def test_login_valido_retorna_token(client):
    resp = client.post("/login", json=TEST_USER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_senha_incorreta_retorna_400(client):
    resp = client.post(
        "/login", json={"email": TEST_USER["email"], "password": "errada"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Email ou Senha incorretos."


def test_me_retorna_usuario_autenticado(client, auth_headers):
    resp = client.get("/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == TEST_USER["email"]
    assert resp.json()["role"] == "ADMIN"


def test_rota_protegida_sem_token_retorna_401(client):
    assert client.get("/clientes").status_code == 401
    assert client.get("/me").status_code == 401


def test_token_invalido_retorna_401(client):
    resp = client.get("/clientes", headers={"Authorization": "Bearer token-falso"})
    assert resp.status_code == 401
