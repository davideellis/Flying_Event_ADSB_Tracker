from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.dependencies import clear_session, set_session
from app.models import User
from app.services.auth import (
    authenticate_user,
    consume_password_reset_token,
    issue_password_reset_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="src/app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Invalid email or password."},
            status_code=400,
        )
    response = RedirectResponse(url="/admin", status_code=303)
    set_session(request, response, user)
    return response


@router.post("/logout")
def logout_action():
    response = RedirectResponse(url="/auth/login", status_code=303)
    clear_session(response)
    return response


@router.get("/reset", response_class=HTMLResponse)
def reset_page(request: Request):
    return templates.TemplateResponse(request, "auth/reset_request.html", {"message": None})


@router.post("/reset", response_class=HTMLResponse)
def reset_request(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email.lower()))
    token_value = None
    if user:
        token = issue_password_reset_token(db, user)
        db.commit()
        token_value = token
    return templates.TemplateResponse(
        request,
        "auth/reset_request.html",
        {
            "message": "If that account exists, a reset token has been issued for local development.",
            "token_value": token_value,
            "base_url": get_settings().password_reset_base_url,
        },
    )


@router.get("/reset/complete", response_class=HTMLResponse)
def reset_complete_page(request: Request, token: str = ""):
    return templates.TemplateResponse(request, "auth/reset_complete.html", {"token": token, "error": None})


@router.post("/reset/complete", response_class=HTMLResponse)
def reset_complete_action(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    success = consume_password_reset_token(db, token, new_password)
    if not success:
        return templates.TemplateResponse(
            request,
            "auth/reset_complete.html",
            {"token": token, "error": "Reset token is invalid or expired."},
            status_code=400,
        )
    db.commit()
    return templates.TemplateResponse(
        request,
        "auth/reset_complete.html",
        {"token": "", "error": None, "message": "Password updated. You can log in now."},
    )
