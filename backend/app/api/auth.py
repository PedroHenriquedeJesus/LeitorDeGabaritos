from datetime import datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, hash_session_token
from app.core.config import get_settings
from app.core.database import get_db
from app.models import AuthSession, User
from app.schemas import LoginRequest, LoginResponse, MessageRead
from app.services.bootstrap import pwd_context


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if user is None or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario ou senha invalidos")

    token = token_urlsafe(32)
    settings = get_settings()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.utcnow() + timedelta(hours=max(1, settings.auth_session_hours)),
    )
    db.add(auth_session)
    db.commit()
    return LoginResponse(access_token=token, user=user)


@router.post("/logout", response_model=MessageRead)
def logout(
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> MessageRead:
    db.delete(auth_session)
    db.commit()
    return MessageRead(message="Sessao encerrada")
