"""Authentication router: login and current-user profile."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import security_service

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(data: schemas.SecuritySchema, db: Session = Depends(get_db)):
    user = security_service.authenticate(db, data.email, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou Senha incorretos.",
        )
    token = security_service.create_access_token({"sub": user.email, "role": user.role})
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def me(current: models.User = Depends(security_service.get_current_user)):
    return current
