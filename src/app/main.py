from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select, text

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import User
from app.routers import admin, auth, public
from app.services.auth import create_user
from app.services.providers import get_adsb_provider
from app.services.worker import poller_loop


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_runtime_schema()


def _ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    if "events" not in inspector.get_table_names():
        return
    event_columns = {column["name"] for column in inspector.get_columns("events")}
    if "show_passenger_name_public" not in event_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE events ADD COLUMN show_passenger_name_public BOOLEAN NOT NULL DEFAULT 0"
                )
            )


def bootstrap_admin() -> None:
    with SessionLocal() as db:
        existing = db.scalar(select(User).limit(1))
        if existing:
            return
        settings = get_settings()
        create_user(
            db,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            display_name="Initial Admin",
        )
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    bootstrap_admin()

    app.state.stop_event = asyncio.Event()
    app.state.worker_task = None
    app.state.adsb_provider = get_adsb_provider().name
    if get_settings().adsb_worker_enabled:
        app.state.worker_task = asyncio.create_task(poller_loop(app.state.stop_event))

    yield

    app.state.stop_event.set()
    if app.state.worker_task is not None:
        await app.state.worker_task



def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.mount("/static", StaticFiles(directory="src/app/static"), name="static")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "adsb_provider": app.state.adsb_provider,
            "worker_enabled": get_settings().adsb_worker_enabled,
        }

    return app


app = create_app()
