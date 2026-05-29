# Client Management & Pipefy Integration

API interna para gerenciar clientes e seus patrimônios investidos, mapeando as
ações para o Pipefy. A persistência é feita em banco local (SQLite), mas as
**queries/mutations GraphQL seguem a sintaxe oficial da API do Pipefy** — trocar
a simulação por chamadas reais é apenas substituir o transporte.

Inclui **autenticação JWT** (operador) + **dashboard web** servido pela própria
API e **testes E2E em Cypress** além dos testes de unidade/integração em pytest.

> Convenção: o **código** (identificadores, funções, comentários) está em
> **inglês**; o **contrato externo** (rotas, campos do payload e valores de
> status/prioridade) permanece em **português**, conforme exigido pelo enunciado
> do teste (`cliente_nome`, `valor_patrimonio`, `"Aguardando Análise"`, …).

## Stack

- **Python 3.11 + FastAPI** (base: FastAPI)
- **SQLAlchemy 2 + SQLite** (zero configuração; troca para PostgreSQL via `DATABASE_URL`)
- **Pydantic v2** para validação (incl. e-mail)
- **JWT (PyJWT) + bcrypt** para autenticação
- **pytest** (unidade/integração) e **Cypress** (E2E)

## Estrutura de pastas

A organização isola as **regras de negócio** das bordas (HTTP e banco):

```
app/
├── main.py                  # bootstrap do FastAPI + routers + seed do admin
├── config.py                # constantes/ambiente (status, limiar, JWT, webhook)
├── database.py              # engine, Session e dependency get_db
├── models.py                # tabelas ORM: Client, User, WebhookEvent
├── schemas.py               # contratos de entrada/saída (Pydantic)
├── repository.py            # acesso a dados (o único que monta queries SQL)
├── routers/
│   ├── auth.py              # POST /login, GET /me
│   ├── clients.py           # POST /clientes, GET /clientes   (Fluxo 1)
│   └── webhooks.py          # POST /webhooks/...               (Fluxo 2)
├── services/
│   ├── client_service.py    # REGRAS DE NEGÓCIO (status, prioridade, idempotência)
│   ├── security_service.py  # hash bcrypt, JWT, get_current_user, webhook token
│   └── pipefy_client.py     # mutations GraphQL do Pipefy (createCard/updateCardField)
└── static/index.html        # dashboard web (servido em GET /)
tests/                       # testes pytest
cypress/e2e/                 # testes E2E (Cypress)
```

**Fluxo de uma requisição:** `router` (HTTP) → `service` (domínio) → `repository`
(persistência) e `pipefy_client` (integração). Cada camada tem uma só
responsabilidade, e o domínio não conhece FastAPI nem SQL — aplicando KISS, DRY
(uma fonte para cada regra) e YAGNI (sem abstrações especulativas).

## Autenticação

- **Operador (POST/GET `/clientes`, `/me`)**: protegido por **JWT Bearer**. Faça
  login em `POST /login` e envie `Authorization: Bearer <token>`.
- **Webhook (`/webhooks/pipefy/card-updated`)**: o Pipefy não envia JWT, então é
  validado por um **segredo compartilhado** no header `X-Webhook-Token` — padrão
  correto para chamadas máquina-a-máquina.
- **Admin semeado no startup** (idempotente): `admin@mundoinvest.com` / `admin123`.

Variáveis de ambiente relevantes (com defaults para dev):

| Variável | Default | Uso |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | assinatura do JWT (HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | validade do token |
| `WEBHOOK_TOKEN` | `dev-webhook-secret` | segredo do header do webhook |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@mundoinvest.com` / `admin123` | admin semeado |
| `DATABASE_URL` | `sqlite:///./clientes.db` | banco |

## Como executar localmente

```bash
# 1. Ambiente virtual (opcional, recomendado)
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/Mac: source .venv/bin/activate

# 2. Dependências
pip install -r requirements.txt

# 3. Subir a API + dashboard
uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000`:
- **Dashboard:** `http://127.0.0.1:8000/` (faça login com o admin semeado)
- **Docs interativas:** `http://127.0.0.1:8000/docs`

O banco `clientes.db` é criado automaticamente.

## Como rodar os testes

### Unidade/integração (pytest)

```bash
pytest -q
```

SQLite em memória isolado por execução (não toca o banco real). Cobre os três
cenários obrigatórios + autenticação e proteção das rotas:

1. Criação de cliente com payload válido e persistência.
2. Regra de prioridade pelo patrimônio no webhook (inclui o limiar exato).
3. Bloqueio de `event_id` duplicado (idempotência).
4. Login, `/me`, 401 sem token e 401 com token de webhook inválido.

### E2E (Cypress)

Com a API rodando (`uvicorn ...`) em outro terminal:

```bash
npm install
npx cypress run        # headless  |  npx cypress open para interativo
```

Exercita login pela UI, os dois fluxos e a idempotência direto no dashboard,
gerando screenshots em `cypress/screenshots/`.

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
TOKEN="<cole o access_token aqui>"
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

Resposta (`201`): cliente salvo com `status: "Aguardando Análise"` e o
`pipefy_card_id` retornado pela mutation `createCard`. O corpo também devolve
`pipefy_mutations` com o GraphQL exato enviado.

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

Resposta (`200`): cliente atualizado para `status: "Processado"` e
`prioridade: "prioridade_alta"` (pois 250000 ≥ 200000). Reenviar o mesmo
`event_id` retorna `200` com aviso de já processado, sem reprocessar.

## As mutations GraphQL do Pipefy

Concentradas em `app/services/pipefy_client.py`, no formato exato da API oficial:

- **`createCard`** (Fluxo 1) — cria o card no pipe. `input: CreateCardInput!` com
  `pipe_id`, `title` e `fields_attributes` (lista de `FieldValueInput` com
  `field_id`/`field_value`).
  Doc: <https://api-docs.pipefy.com/reference/mutations/createCard/>

- **`updateCardField`** (Fluxo 2) — atualiza um campo do card.
  `input: UpdateCardFieldInput!` com `card_id`, `field_id`, `new_value`.
  Chamamos uma vez por campo (status e prioridade).
  Doc: <https://api-docs.pipefy.com/reference/mutations/updateCardField/>

A montagem usa **variáveis GraphQL** (`$input`), prática recomendada que evita
interpolação manual de strings e injeção. O método `_simulate_send` faz o papel
do transporte: hoje loga o payload e devolve uma resposta no mesmo shape do
Pipefy; para integrar de verdade, basta trocá-lo por um POST autenticado a
`https://api.pipefy.com/graphql`. A resposta dos endpoints expõe `pipefy_mutations`,
o que alimenta o painel **"Pipefy GraphQL · Live Wire"** do dashboard.

## Visão de Produção (AWS)

Para escalar esta estrutura na AWS de forma serverless e desacoplada:

- **API Gateway + AWS Lambda**: os endpoints viram funções Lambda atrás do API
  Gateway. A app FastAPI roda como está via um adaptador (ex.: *Mangum*),
  escalando horizontalmente sem gerenciar servidores e pagando por uso. Auth JWT
  pode ser validada por um **Lambda Authorizer**; o segredo do webhook por um
  authorizer dedicado ou WAF.

- **Banco de dados**:
  - **DynamoDB** encaixa bem no acesso por chave (cliente por e-mail, evento por
    `event_id`). A idempotência fica natural com `PutItem` +
    `ConditionExpression: attribute_not_exists(event_id)` — escrita só ocorre se o
    evento não existir, eliminando duplicidade sem corrida. TTL automático
    expira eventos antigos.
  - **RDS (PostgreSQL)** é a escolha se houver relacionamentos/relatórios e
    consultas SQL ricas; usar **RDS Proxy** para gerenciar o pool de conexões com
    as Lambdas.

- **Processamento de webhook resiliente**: o API Gateway recebe o webhook e
  publica numa fila **SQS** (ou tópico **SNS**), respondendo `200` rápido ao
  Pipefy. Uma Lambda consome a fila e processa de forma assíncrona; falhas vão
  para uma **DLQ** e podem ser reprocessadas. A idempotência por `event_id`
  garante segurança mesmo com reentregas (Pipefy/SQS entregam *at-least-once*).

- **Observabilidade e segredos**: **CloudWatch** para logs/métricas/alarmes e
  **Secrets Manager** para `SECRET_KEY`, `WEBHOOK_TOKEN`, token da API do Pipefy
  e credenciais do banco.

Fluxo em produção:
`Pipefy → API Gateway → SQS → Lambda (regra de negócio) → DynamoDB/RDS`,
com a chamada `updateCardField` voltando ao Pipefy a partir da Lambda.
