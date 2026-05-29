from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from repositories.base_repository import BaseRepository, get_db
from fastapi import Depends, Header, HTTPException, Request
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.models import User, UserRole, AccessLog, AccessLogType
from zoneinfo import ZoneInfo
from http import HTTPStatus
from jwt import encode, decode
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

import bcrypt
import os

security = HTTPBearer()

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-me')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 1 dia = 24 horas * 60 minutos
# Webhooks não carregam JWT: validamos por um segredo de header.
WEBHOOK_TOKEN = os.getenv('WEBHOOK_TOKEN', 'dev-webhook-secret')
# Fuso horário local: UTC-3
LOCAL_TIMEZONE = ZoneInfo('America/Sao_Paulo')
UTC_TIMEZONE = ZoneInfo('UTC')


class SecurityRepository:
    def __init__(self, base_repository: BaseRepository = Depends()):
        self.base_repository = base_repository

    @property
    def _entity(self):
        return User

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def create_access_token(self, data):
        to_encode = data.dict().copy() if hasattr(data, 'dict') else data.copy()
        # Tokens JWT devem usar UTC (padrão)
        expire = datetime.now(tz=UTC_TIMEZONE) + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({'exp': expire})
        encoded_jwt = encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_user(self, data):
        user = self.base_repository.db.query(self._entity).filter(
            self._entity.email == data.email
        ).first()
        if not user:
            return None
        password_attempt = data.password.encode('utf-8')
        stored_hash = user.password.encode('utf-8')
        if bcrypt.checkpw(password_attempt, stored_hash):
            return user
        return None

    @staticmethod
    def get_current_user(token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
        try:
            payload = decode(token.credentials, SECRET_KEY,
                             algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            role_str: str = payload.get("role")

            role = None
            for user_role in UserRole:
                if user_role.value == role_str:
                    role = user_role
                    break

            if not role:
                raise Exception()

            user = db.query(User).filter(User.email == email).first()
            if not user:
                raise Exception()

            return {"user": user, "user_id": user.id, "role": role}
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token expirado. Faça login novamente.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except (InvalidTokenError, Exception):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Acesso não autorizado.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def require_webhook_token(x_webhook_token: str = Header(default=None)):
        """Valida o segredo compartilhado do webhook (Pipefy não envia JWT)."""
        if x_webhook_token != WEBHOOK_TOKEN:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token de webhook inválido.",
            )

    @staticmethod
    def create_access_log(db: Session, user_id: int, log_type: AccessLogType, request: Request = None):
        """Cria um log de acesso (login/logout)."""
        ip_address = None
        user_agent = None
        if request:
            if request.client:
                ip_address = request.client.host
            user_agent = request.headers.get("user-agent")
            if user_agent and len(user_agent) > 500:
                user_agent = user_agent[:500]

        access_log = AccessLog(
            user_id=user_id,
            log_type=log_type.value,
            logged_at=datetime.now(tz=LOCAL_TIMEZONE),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(access_log)
        db.commit()
        return access_log

    @staticmethod
    def require_admin(current_user: dict):
        """Garante que o usuário atual é admin ou superAdmin."""
        role = current_user.get("role")
        if role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Seu usuário não tem permissão para realizar a ação.',
            )
