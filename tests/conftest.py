from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.db import Base, get_db
from app.main import create_app
from app.models import Event, EventAircraft
from app.services.auth import create_user


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        yield db
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(session: Session):
    app = create_app()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded_admin(session: Session):
    admin = create_user(session, "admin@example.com", "Password123!", "Admin User")
    session.commit()
    return admin


@pytest.fixture()
def seeded_event(session: Session):
    event = Event(
        name="Young Eagles Demo",
        slug="young-eagles-demo",
        airport_code="KPWK",
        airport_name="Chicago Executive",
        latitude=42.114222,
        longitude=-87.901472,
        map_center_latitude=42.114222,
        map_center_longitude=-87.901472,
        default_zoom=11,
        event_radius_nm=10,
        return_radius_nm=2,
        arrival_hold_seconds=60,
        is_active=True,
        is_published=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    aircraft = EventAircraft(event=event, tail_number="N2468A")
    session.add_all([event, aircraft])
    session.commit()
    return event
