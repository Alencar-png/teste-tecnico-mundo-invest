from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, TypeDecorator, DateTime
from sqlalchemy.orm import relationship, deferred
from config.database import Base
from datetime import datetime
from zoneinfo import ZoneInfo
import enum

# Fuso horário local: UTC-3
LOCAL_TIMEZONE = ZoneInfo('America/Sao_Paulo')  # UTC-3


def _utcnow():
    return datetime.now(tz=ZoneInfo('UTC'))


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "superAdmin"
    ADMIN = "admin"
    BASIC_USER = "basicUser"


class UserRoleType(TypeDecorator):
    """Type decorator para mapear corretamente os valores do enum UserRole."""
    impl = String
    cache_ok = True

    def __init__(self, length=20):
        super().__init__(length=length)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, UserRole):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        for role in UserRole:
            if role.value == value:
                return role
        return value


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    email = Column(String(255), unique=True, nullable=False)
    password = deferred(Column(String(255), nullable=False))
    role = Column(UserRoleType(), nullable=False, default=UserRole.BASIC_USER)


class AccessLogType(str, enum.Enum):
    """Tipos de log de acesso."""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGOUT_EXPIRATION = "logout_expiration"


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    log_type = Column(String(50), nullable=False)
    logged_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(tz=LOCAL_TIMEZONE))
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    user = relationship("User", backref="access_logs")


class Client(Base):
    """Cliente e seu patrimônio investido (contrato de campos em PT)."""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    tipo_solicitacao = Column(String(255), nullable=False)
    valor_patrimonio = Column(Numeric(18, 2), nullable=False)
    status = Column(String(50), nullable=False)
    prioridade = Column(String(50), nullable=True)
    # Id do card retornado pelo Pipefy ao criar (aqui, simulado).
    pipefy_card_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class WebhookEvent(Base):
    """Eventos de webhook já processados — base da idempotência."""
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    card_id = Column(String(255), nullable=True)
    cliente_email = Column(String(255), nullable=True)
    processed_at = Column(DateTime(timezone=True), default=_utcnow)
