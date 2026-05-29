# Client Management & Pipefy Integration

API interna para gerenciar clientes e seus patrimônios investidos, mapeando as
ações para o Pipefy. A persistência é em **MySQL** (via Docker), mas as
**queries/mutations GraphQL seguem a sintaxe oficial da API do Pipefy** — trocar
a simulação por chamadas reais é apenas substituir o transporte.

A estrutura de pastas e o estilo de código **espelham a base de referência
[`fastapi-example-mysql`](https://github.com/Alencar-png/fastapi-example-mysql)**:
pastas no plural na raiz, `repositories` em classes com um `BaseRepository`/`CRUDBase`,
autenticação via `SecurityRepository` (JWT/bcrypt) e migrações Alembic.

Inclui **autenticação JWT**, **dashboard web** servido pela própria API e
**testes E2E (Cypress)** além dos testes de unidade/integração (pytest).

## Stack

- **Python 3.11 + FastAPI**
- **MySQL 8 + SQLAlchemy 2 + Alembic** (via `docker-compose`)
- **Pydantic v2** (validação, incl. e-mail)
- **PyJWT + bcrypt** (autenticação, mesmo padrão da base)
- **pytest** (unidade/integração, SQLite em memória) e **Cypress** (E2E)

## Estrutura de pastas (espelha a base)

```
main.py                      # cria o app FastAPI, registra routers, serve o dashboard
config/
  database.py                # engine (MySQL via .env; SQLite de fallback p/ testes), Base
  settings.py                # constantes de domínio (status, limiar de prioridade, admin)
models/
  models.py                  # User, UserRole, AccessLog, Client, WebhookEvent
repositories/                # acesso a dados + REGRAS DE NEGÓCIO (sem camada services)
  base_repository.py         # BaseRepository (CRUD genérico) + CRUDBase (ABC) + get_db
  security_repository.py     # JWT, bcrypt, get_current_user, require_webhook_token, logs
  clients_repository.py      # criação de cliente, prioridade e idempotência (Fluxos 1 e 2)
  webhook_events_repository.py # idempotência (eventos já processados)
  pipefy_repository.py       # mutations GraphQL do Pipefy (createCard / updateCardField)
routers/                     # só HTTP (guard-clauses + chamadas aos repositories)
  security.py                # POST /login, POST /logout, GET /me
  clients.py                 # POST /clientes, GET /clientes      (Fluxo 1)
  webhooks.py                # POST /webhooks/pipefy/card-updated  (Fluxo 2)
schemas/                     # contratos Pydantic (entrada/saída)
  security_schemas.py · client_schemas.py · webhook_schemas.py
alembic/                     # migrações (schema do MySQL)
static/index.html            # dashboard web (servido em GET /)
tests/                       # pytest (test_*_router.py)
cypress/e2e/                 # testes E2E
```

**Fluxo de uma requisição:** `router` (HTTP) → `repository` (dados + regra de
negócio) → `base_repository` (CRUD). Os repositories são injetados via
`Depends()`; um repository pode compor outros (ex.: `ClientsRepository` injeta
`PipefyRepository` e `WebhookEventsRepository`). KISS, DRY e YAGNI.

> **Contrato em PT, código em EN:** identificadores/comentários em inglês, mas os
> endpoints, campos do payload e valores (`/clientes`, `cliente_nome`,
> `"Aguardando Análise"`, `prioridade_alta`) permanecem em português, conforme o
> enunciado. Por isso não usamos o prefixo `/api` da base.

## Autenticação

- **Operador (`POST`/`GET /clientes`, `/me`)**: **JWT Bearer**. Faça login em
  `POST /login` e envie `Authorization: Bearer <token>`.
- **Webhook**: o Pipefy não envia JWT → validado por **segredo compartilhado** no
  header `X-Webhook-Token` (padrão máquina-a-máquina).
- **Admin semeado** no startup (idempotente): `admin@mundoinvest.com` / `admin123`.

## Como executar localmente

```bash
# 1. Configurar ambiente
cp .env.example .env            # ajuste segredos se quiser

# 2. Subir o MySQL (e o Adminer em :8080)
docker compose up -d

# 3. Dependências Python
python -m venv .venv && . .venv/Scripts/activate   # (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# 4. Criar o schema (migrações)
alembic upgrade head

# 5. Subir a API + dashboard
uvicorn main:app --reload
```

- **Dashboard:** http://127.0.0.1:8000/ (login com o admin semeado)
- **Docs (Swagger):** http://127.0.0.1:8000/docs
- **Adminer (MySQL):** http://127.0.0.1:8080

> O startup também roda `create_all` como rede de segurança em dev; em produção o
> caminho oficial de schema é o Alembic (`alembic upgrade head`).

## Como rodar os testes

### Unidade/integração (pytest)

```bash
pytest
```

Usa **SQLite em memória** (`TESTING=1`), isolado por teste — não precisa de MySQL.
Cobre os três cenários obrigatórios + autenticação:

1. Criação de cliente com payload válido e persistência.
2. Regra de prioridade pelo patrimônio no webhook (inclui o limiar exato 200.000).
3. Bloqueio de `event_id` duplicado (idempotência).
4. Login, `/me`, proteção das rotas (401/403) e token de webhook inválido (401).

### E2E (Cypress)

Com a API rodando:

```bash
npm install
npx cypress run        # headless  |  npx cypress open para interativo
```

Login pela UI, os dois fluxos e a idempotência no dashboard real; screenshots em
`cypress/screenshots/`.

## Exemplos de requisição (curl)

### 0. Login (obtém o token)

```bash
curl -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@mundoinvest.com", "password": "admin123"}'
# -> {"access_token": "<JWT>", "token_type": "bearer"}
```

### Fluxo 1 — Criar cliente (requer Bearer)

```bash
TOKEN="<access_token>"
curl -X POST http://127.0.0.1:8000/clientes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "cliente_nome": "João Silva",
    "cliente_email": "joao.silva@example.com",
    "tipo_solicitacao": "Atualização cadastral",
    "valor_patrimonio": 250000
  }'
```

`201`: cliente salvo com `status: "Aguardando Análise"` e o `pipefy_card_id` da
mutation `createCard`. O corpo devolve `pipefy_mutations` (o GraphQL exato enviado).

### Fluxo 2 — Webhook de card atualizado (requer X-Webhook-Token)

```bash
curl -X POST http://127.0.0.1:8000/webhooks/pipefy/card-updated \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: dev-webhook-secret" \
  -d '{
    "event_id": "evt_123",
    "card_id": "card_456",
    "cliente_email": "joao.silva@example.com",
    "timestamp": "2026-05-18T12:00:00Z"
  }'
```

`200`: cliente atualizado para `status: "Processado"` e `prioridade: "prioridade_alta"`
(250000 ≥ 200000). Reenviar o mesmo `event_id` retorna `200` com aviso, sem reprocessar.

## As mutations GraphQL do Pipefy

Em `repositories/pipefy_repository.py`, no formato exato da API oficial:

- **`createCard`** (Fluxo 1) — `input: CreateCardInput!` com `pipe_id`, `title` e
  `fields_attributes` (lista de `FieldValueInput` com `field_id`/`field_value`).
  Doc: <https://api-docs.pipefy.com/reference/mutations/createCard/>
- **`updateCardField`** (Fluxo 2) — `input: UpdateCardFieldInput!` com `card_id`,
  `field_id`, `new_value`. Chamada uma vez por campo (status e prioridade).
  Doc: <https://api-docs.pipefy.com/reference/mutations/updateCardField/>

Usa **variáveis GraphQL** (`$input`) — sem interpolação de string. O método
`_simulate_send` é o transporte simulado (loga o payload e devolve o mesmo shape
do Pipefy); integrar de verdade é só um POST autenticado a `api.pipefy.com/graphql`.
A resposta dos endpoints expõe `pipefy_mutations`, alimentando o painel
**"Pipefy GraphQL · Live Wire"** do dashboard.

## Visão de Produção (AWS)

- **API Gateway + AWS Lambda**: os endpoints viram Lambdas atrás do API Gateway
  (FastAPI via *Mangum*). JWT validado por **Lambda Authorizer**; o segredo do
  webhook por um authorizer dedicado / WAF.
- **Banco**:
  - **RDS (MySQL/PostgreSQL)** mantém o mesmo modelo relacional + Alembic; usar
    **RDS Proxy** para o pool de conexões das Lambdas.
  - **DynamoDB** é alternativa para acesso por chave; idempotência natural com
    `PutItem` + `ConditionExpression: attribute_not_exists(event_id)` e TTL.
- **Webhook resiliente**: API Gateway → **SQS** (responde 200 rápido) → Lambda
  consumidora processa; falhas vão p/ **DLQ**. A idempotência por `event_id`
  protege contra reentregas (*at-least-once*).
- **Observabilidade/segredos**: **CloudWatch** (logs/métricas) e **Secrets
  Manager** (`SECRET_KEY`, `WEBHOOK_TOKEN`, token do Pipefy, credenciais do banco).

Fluxo: `Pipefy → API Gateway → SQS → Lambda → RDS/DynamoDB`, com `updateCardField`
voltando ao Pipefy a partir da Lambda.
