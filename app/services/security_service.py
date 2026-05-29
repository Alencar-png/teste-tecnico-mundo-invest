"""Authentication and authorization.

Reproduces the fastapi-example-mysql base pattern: bcrypt password hashing,
HS256 JWT with expiry, and a get_current_user dependency that validates the
token against the database. Webhooks use a header secret (require_webhook_token).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import config, models, repository
from app.database import get_db

# tokenUrl is used by Swagger for the "Authorize" button; login accepts JSON.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ---------- Passwords (bcrypt) ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------- Tokens (JWT) ----------
def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def authenticate(db: Session, email: str, password: str) -> models.User | None:
    user = repository.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


# ---------- Dependencies ----------
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise cred_exc
    except jwt.PyJWTError:
        raise cred_exc

    user = repository.get_user_by_email(db, email)
    if user is None:
        raise cred_exc
    return user


def require_webhook_token(x_webhook_token: str | None = Header(default=None)) -> None:
    """Validates the shared webhook secret (Pipefy does not send a JWT)."""
    if x_webhook_token != config.WEBHOOK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de webhook inválido.",
        )
