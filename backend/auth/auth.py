from sqlalchemy.orm import Session

from auth.password_utils import hash_password, verify_password
from auth.roles import ROLE_USER
from models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    role: str = ROLE_USER,
) -> User:
    user = User(
        full_name=full_name.strip(),
        email=email.lower(),
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

