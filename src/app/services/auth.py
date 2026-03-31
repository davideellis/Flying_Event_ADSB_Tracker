from __future__ import annotations

from datetime import datetime, timedelta
from secrets import token_urlsafe

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PasswordResetToken, User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_user(db: Session, email: str, password: str, display_name: str) -> User:
    user = User(email=email.lower(), password_hash=hash_password(password), display_name=display_name)
    db.add(user)
    db.flush()
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.lower(), User.is_active.is_(True)))
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def issue_password_reset_token(db: Session, user: User, now: datetime | None = None) -> str:
    issued_at = now or datetime.utcnow()
    raw_token = token_urlsafe(32)
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password(raw_token),
        expires_at=issued_at + timedelta(hours=1),
    )
    db.add(token)
    db.flush()
    return raw_token


def consume_password_reset_token(db: Session, raw_token: str, new_password: str, now: datetime | None = None) -> bool:
    current_time = now or datetime.utcnow()
    candidates = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at >= current_time
        )
    ).all()
    for candidate in candidates:
        if verify_password(raw_token, candidate.token_hash):
            user = db.get(User, candidate.user_id)
            if not user:
                return False
            user.password_hash = hash_password(new_password)
            candidate.used_at = current_time
            return True
    return False
