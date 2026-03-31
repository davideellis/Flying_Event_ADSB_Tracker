from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import URLSafeSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

serializer = URLSafeSerializer(get_settings().secret_key, salt="session")


def set_session(request: Request, response, user: User) -> None:
    payload = serializer.dumps({"user_id": user.id})
    response.set_cookie(
        get_settings().session_cookie_name,
        payload,
        httponly=True,
        samesite="lax",
        secure=False,
    )


def clear_session(response) -> None:
    response.delete_cookie(get_settings().session_cookie_name)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    cookie = request.cookies.get(get_settings().session_cookie_name)
    if not cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = serializer.loads(cookie)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc

    user = db.scalar(select(User).where(User.id == payload.get("user_id"), User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
