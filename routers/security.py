from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request

from models.models import AccessLogType, User
from repositories.security_repository import SecurityRepository
from schemas.security_schemas import SecuritySchema, Token, UserOut

security = APIRouter()


@security.post("/login", response_model=Token)
def login(data: SecuritySchema, request: Request, repo: SecurityRepository = Depends()):
    user = repo.verify_user(data)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Email ou Senha incorretos."
        )
    token = repo.create_access_token({"sub": user.email, "role": user.role.value})
    SecurityRepository.create_access_log(
        db=repo.base_repository.db,
        user_id=user.id,
        log_type=AccessLogType.LOGIN,
        request=request,
    )
    return Token(access_token=token)


@security.post("/logout")
def logout(
    request: Request,
    current_user: dict = Depends(SecurityRepository.get_current_user),
    repo: SecurityRepository = Depends(),
):
    SecurityRepository.create_access_log(
        db=repo.base_repository.db,
        user_id=current_user["user_id"],
        log_type=AccessLogType.LOGOUT,
        request=request,
    )
    return {"detail": "Logout efetuado."}


@security.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(SecurityRepository.get_current_user)):
    user: User = current_user["user"]
    return UserOut(id=user.id, email=user.email, role=user.role.value)
