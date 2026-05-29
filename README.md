# Client Management & Pipefy Integration

API interna para gerenciar clientes e seus patrimônios investidos, mapeando as
ações para o Pipefy. A persistência é feita em banco local (SQLite), mas as
**queries/mutations GraphQL seguem a sintaxe oficial da API do Pipefy** — trocar
a simulação por chamadas reais é apenas substituir o transporte.

## Stack

- **Python 3.11 + FastAPI** (base sugerida: FastAPI)
- **SQLAlchemy 2 + SQLite** (zero configuração; troca para PostgreSQL via `DATABASE_URL`)
- **Pydantic v2** para validação (incl. e-mail)
- **pytest** para os testes automatizados

## Estrutura de pastas

A organização isola as **regras de negócio** das bordas (HTTP e banco):

```
app/
├── main.py                  # bootstrap do FastAPI + registro dos routers
├── config.py                # constantes/ambiente (status, limiar, pipe_id)
├── database.py              # engine, Session e dependency get_db
├── models.py                # tabelas ORM: Cliente, WebhookEvent
├── schemas.py               # contratos de entrada/saída (Pydantic)
├── repository.py            # acesso a dados (o único que monta queries SQL)
├── routers/
│   ├── clientes.py          # POST /clientes        (Fluxo 1)
│   └── webhooks.py          # POST /webhooks/...     (Fluxo 2)
└── services/
    ├── cliente_service.py   # REGRAS DE NEGÓCIO (status, prioridade, idempotência)
    └── pipefy_client.py     # mutations GraphQL do Pipefy (createCard / updateCardField)
tests/                       # testes automatizados (pytest)
```

**Fluxo de uma requisição:** `router` (HTTP) → `service` (domínio) → `repository`
(persistência) e `pipefy_client` (integração). Cada camada tem uma só
responsabilidade, e o domínio não conhece FastAPI nem SQL — aplicando KISS, DRY
(uma fonte para cada regra) e YAGNI (sem abstrações especulativas).

## Como executar localmente

```bash
# 1. Ambiente virtual (opcional, recomendado)
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/Mac: source .venv/bin/activate

# 2. Dependências
pip install -r requirements.txt

# 3. Subir a API
uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. Docs interativas em
`http://127.0.0.1:8000/docs`. O banco `clientes.db` é criado automaticamente.

## Como rodar os testes

```bash
pytest -q
```

Os testes usam um SQLite em memória isolado por execução (não tocam o banco real)
e cobrem os três cenários obrigatórios:

1. Criação de cliente com payload válido e persistência.
2. Aplicação da regra de prioridade pelo patrimônio no webhook.
3. Bloqueio de `event_id` duplicado (idempotência).

## Exemplos de requisição (curl)

### Fluxo 1 — Criar cliente

```bash
curl -X POST http://127.0.0.1:8000/clientes \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_nome": "João Silva",
    "cliente_email": "joao.silva@example.com",
    "tipo_solicitacao": "Atualização cadastral",
    "valor_patrimonio": 250000
  }'
```

Resposta (`201`): cliente salvo com `status: "Aguardando Análise"` e o
`pipefy_card_id` retornado pela mutation `createCard`.

### Fluxo 2 — Webhook de card atualizado

```bash
curl -X POST http://127.0.0.1:8000/webhooks/pipefy/card-updated \
  -H "Content-Type: application/json" \
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
interpolação manual de strings e injeção. O método `_simular_envio` faz o papel
do transporte: hoje loga o payload e devolve uma resposta no mesmo shape do
Pipefy; para integrar de verdade, basta trocá-lo por um POST autenticado a
`https://api.pipefy.com/graphql`.

## Visão de Produção (AWS)

Para escalar esta estrutura na AWS de forma serverless e desacoplada:

- **API Gateway + AWS Lambda**: os dois endpoints viram funções Lambda atrás do
  API Gateway. A app FastAPI roda como está via um adaptador (ex.: *Mangum*),
  escalando horizontalmente sem gerenciar servidores e pagando por uso.

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
  **Secrets Manager** para o token da API do Pipefy e credenciais do banco.

Fluxo em produção:
`Pipefy → API Gateway → SQS → Lambda (regra de negócio) → DynamoDB/RDS`,
com a chamada `updateCardField` voltando ao Pipefy a partir da Lambda.
