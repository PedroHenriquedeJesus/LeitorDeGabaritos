from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_database(db: Session, initial_admin_username: str, initial_admin_password: str) -> None:
    has_user = db.scalar(select(User.id).limit(1))
    if has_user:
        return

    username = initial_admin_username.strip()
    if not username or not initial_admin_password:
        raise RuntimeError(
            "Banco sem administrador. Defina INITIAL_ADMIN_USERNAME e "
            "INITIAL_ADMIN_PASSWORD conforme o README antes da primeira inicializacao."
        )
    if len(initial_admin_password) < 8 or len(initial_admin_password.encode("utf-8")) > 72:
        raise RuntimeError("A senha inicial deve ter entre 8 e 72 bytes.")

    admin = User(
        username=username,
        full_name="Administrador CorretorApp",
        password_hash=pwd_context.hash(initial_admin_password),
        role=UserRole.admin,
    )
    db.add(admin)
    db.commit()
