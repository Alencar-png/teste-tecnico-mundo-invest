"""Domain settings (statuses, priority rule, admin seed).

The status/priority VALUES stay in Portuguese on purpose — they are part of the
contract defined by the technical-test specification.
"""
import os

# Client lifecycle statuses (mirror the Pipefy phases/labels).
STATUS_INITIAL = "Aguardando Análise"
STATUS_PROCESSED = "Processado"

# Business rule: net-worth threshold for high priority.
HIGH_PRIORITY_THRESHOLD = 200_000
PRIORITY_HIGH = "prioridade_alta"
PRIORITY_NORMAL = "prioridade_normal"

# Admin user seeded on startup.
DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@mundoinvest.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
