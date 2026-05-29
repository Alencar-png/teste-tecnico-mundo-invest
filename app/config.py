"""Configurações da aplicação.

Centraliza valores que mudariam entre ambientes (local, produção). Em produção
estes viriam de variáveis de ambiente / secrets manager.
"""
import os

# Banco local. Em produção seria a URL do RDS/PostgreSQL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clientes.db")

# Identificador do pipe no Pipefy onde os cards seriam criados.
PIPEFY_PIPE_ID = os.getenv("PIPEFY_PIPE_ID", "301613")

# Status do ciclo de vida do cliente (espelham as fases/labels no Pipefy).
STATUS_INICIAL = "Aguardando Análise"
STATUS_PROCESSADO = "Processado"

# Regra de negócio: limiar de patrimônio para prioridade alta.
LIMIAR_PRIORIDADE_ALTA = 200_000
PRIORIDADE_ALTA = "prioridade_alta"
PRIORIDADE_NORMAL = "prioridade_normal"
