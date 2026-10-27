from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.models.enums import Role
from app.schemas.user import RegisterRequest


class EmailAlreadyRegistered(Exception):
    pass


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email.lower())).first()


def register_user(db: Session, data: RegisterRequest, role: Role = Role.user) -> User:
    if get_user_by_email(db, data.email):
        raise EmailAlreadyRegistered
    user = User(email=data.email.lower(), hashed_password=hash_password(data.password),
                full_name=data.full_name, phone=data.phone, role=role.value)
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    ok = verify_password(password, user.hashed_password if user else None)
    if not user or not ok or not user.is_active:
        return None
    return user
