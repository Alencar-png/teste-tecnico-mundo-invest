"""Application configuration.

Centralizes values that change between environments (local, production). In
production these would come from environment variables / a secrets manager.
"""
import os

# Local database. In production this would be the RDS/PostgreSQL URL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clientes.db")

# Identifier of the Pipefy pipe where cards would be created.
PIPEFY_PIPE_ID = os.getenv("PIPEFY_PIPE_ID", "301613")

# Client lifecycle statuses (mirror the phases/labels in Pipefy).
# NOTE: values are kept in Portuguese on purpose — they are part of the
# contract defined by the technical test specification.
STATUS_INITIAL = "Aguardando Análise"
STATUS_PROCESSED = "Processado"

# Business rule: net-worth threshold for high priority.
HIGH_PRIORITY_THRESHOLD = 200_000
PRIORITY_HIGH = "prioridade_alta"
PRIORITY_NORMAL = "prioridade_normal"

# ---------- Authentication (JWT + bcrypt) ----------
# Same pattern as the fastapi-example-mysql base: HS256, configurable expiry.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Webhooks do not carry a user JWT: we validate them with a shared header
# secret, which is the correct pattern for machine-to-machine calls.
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "dev-webhook-secret")

# Admin user seeded on startup (in production: via a controlled seed/migration).
DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@mundoinvest.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
