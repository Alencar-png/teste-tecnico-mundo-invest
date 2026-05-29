"""Regras de negócio dos clientes.

É aqui que vivem as decisões do domínio (status inicial, cálculo de prioridade,
idempotência). Os routers só traduzem HTTP <-> service; o repository só persiste.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app import config, models, repository, schemas
from app.services.pipefy_client import PipefyClient


class ClienteJaExisteError(Exception):
    pass


class ClienteNaoEncontradoError(Exception):
    pass


class EventoDuplicadoError(Exception):
    pass


def _calcular_prioridade(valor_patrimonio: Decimal) -> str:
    """Patrimônio >= 200.000 => prioridade alta; caso contrário, normal."""
    if valor_patrimonio >= config.LIMIAR_PRIORIDADE_ALTA:
        return config.PRIORIDADE_ALTA
    return config.PRIORIDADE_NORMAL


def listar_clientes(db: Session) -> list[models.Cliente]:
    """Leitura para o dashboard/KPIs."""
    return repository.listar_clientes(db)


def criar_cliente(
    db: Session, dados: schemas.ClienteCreate, pipefy: PipefyClient
) -> tuple[models.Cliente, list[dict]]:
    """Fluxo 1: persiste o cliente como 'Aguardando Análise' e cria o card.

    Retorna o cliente e as mutations GraphQL enviadas ao Pipefy.
    """
    if repository.buscar_cliente_por_email(db, dados.cliente_email):
        raise ClienteJaExisteError(dados.cliente_email)

    cliente = repository.criar_cliente(
        db,
        nome=dados.cliente_nome,
        email=dados.cliente_email,
        tipo_solicitacao=dados.tipo_solicitacao,
        valor_patrimonio=dados.valor_patrimonio,
        status=config.STATUS_INICIAL,
    )

    # Mapeamento Pipefy: cria o card correspondente (mutation createCard).
    resultado = pipefy.criar_card(
        nome=cliente.nome,
        email=cliente.email,
        valor_patrimonio=cliente.valor_patrimonio,
    )
    cliente.pipefy_card_id = resultado["card"]["id"]
    db.commit()
    db.refresh(cliente)
    return cliente, resultado["mutations"]


def processar_webhook(
    db: Session, dados: schemas.WebhookCardUpdated, pipefy: PipefyClient
) -> tuple[models.Cliente, list[dict]]:
    """Fluxo 2: idempotência -> prioridade -> update no Pipefy -> banco local.

    Retorna o cliente e as mutations GraphQL enviadas ao Pipefy.
    """
    # 1. Idempotência: evento já visto não é reprocessado.
    if repository.evento_ja_processado(db, dados.event_id):
        raise EventoDuplicadoError(dados.event_id)

    # 2. Localiza o cliente e calcula a prioridade pela regra de negócio.
    cliente = repository.buscar_cliente_por_email(db, dados.cliente_email)
    if cliente is None:
        raise ClienteNaoEncontradoError(dados.cliente_email)

    prioridade = _calcular_prioridade(cliente.valor_patrimonio)

    # 3. Mapeamento Pipefy: envia status + prioridade (mutation updateCardField).
    resultado = pipefy.atualizar_card(
        card_id=dados.card_id,
        status=config.STATUS_PROCESSADO,
        prioridade=prioridade,
    )

    # 4. Atualiza o banco local e registra o evento (fecha a idempotência).
    repository.atualizar_cliente(
        db, cliente, status=config.STATUS_PROCESSADO, prioridade=prioridade
    )
    repository.registrar_evento(
        db,
        event_id=dados.event_id,
        card_id=dados.card_id,
        cliente_email=dados.cliente_email,
    )
    return cliente, resultado["mutations"]
