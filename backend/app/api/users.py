from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models import AuthSession, User
from app.schemas import MessageRead, PasswordChange, UserRead
from app.services.bootstrap import pwd_context

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    return user


@router.put("/me/password", response_model=MessageRead)
def change_password(
    payload: PasswordChange,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageRead:
    if not pwd_context.verify(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
    if pwd_context.verify(payload.new_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A nova senha deve ser diferente da atual")
    if len(payload.new_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A senha deve ter no maximo 72 bytes")

    user.password_hash = pwd_context.hash(payload.new_password)
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    return MessageRead(message="Senha alterada. Entre novamente com a nova senha.")
