"""Testes de autenticação (login, /me e proteção de rotas)."""
from tests.conftest import TEST_ADMIN


def test_login_valido_retorna_token(client):
    resp = client.post("/login", json=TEST_ADMIN)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_senha_incorreta_retorna_400(client):
    resp = client.post(
        "/login", json={"email": TEST_ADMIN["email"], "password": "errada"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Email ou Senha incorretos."


def test_me_retorna_usuario_autenticado(client, auth_headers):
    resp = client.get("/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == TEST_ADMIN["email"]
    assert resp.json()["role"] == "admin"


def test_rota_protegida_sem_token_retorna_401(client):
    assert client.get("/clientes").status_code in (401, 403)


def test_token_invalido_retorna_401(client):
    resp = client.get("/clientes", headers={"Authorization": "Bearer token-falso"})
    assert resp.status_code == 401
