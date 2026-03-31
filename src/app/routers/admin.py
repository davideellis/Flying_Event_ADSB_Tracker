from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.dependencies import get_current_user
from app.models import (
    AircraftState,
    Event,
    EventAircraft,
    PassengerAssignmentStatus,
    StateSource,
    User,
)
from app.services.adsb import Observation
from app.services.auth import create_user
from app.services.domain import (
    QueueLimitExceededError,
    activate_passenger,
    enqueue_passenger,
    process_observation,
    record_state_change,
)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="src/app/templates")


def _event_query() -> select:
    return select(Event).options(
        selectinload(Event.aircraft).selectinload(EventAircraft.passenger_assignments),
        selectinload(Event.aircraft).selectinload(EventAircraft.tracks),
    )


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    events = db.scalars(_event_query().order_by(Event.created_at.desc())).all()
    users = db.scalars(select(User).order_by(User.email)).all()
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"user": user, "events": events, "users": users, "error": None},
    )


@router.post("/users")
def create_admin_user(
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    create_user(db, email=email, password=password, display_name=display_name)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_admin_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    users = db.scalars(select(User).where(User.is_active.is_(True))).all()
    if len(users) <= 1:
        raise HTTPException(status_code=400, detail="At least one active admin must remain.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404)
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/events")
def create_event(
    name: str = Form(...),
    slug: str = Form(...),
    airport_code: str = Form(""),
    airport_name: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    default_zoom: int = Form(11),
    event_radius_nm: float = Form(...),
    return_radius_nm: float = Form(...),
    arrival_hold_seconds: int = Form(...),
    is_published: bool = Form(False),
    is_active: bool = Form(False),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = Event(
        name=name,
        slug=slug,
        description=description or None,
        airport_code=airport_code or None,
        airport_name=airport_name or None,
        latitude=latitude,
        longitude=longitude,
        map_center_latitude=latitude,
        map_center_longitude=longitude,
        default_zoom=default_zoom,
        event_radius_nm=event_radius_nm,
        return_radius_nm=return_radius_nm,
        arrival_hold_seconds=arrival_hold_seconds,
        is_published=is_published,
        is_active=is_active,
        created_by_user_id=user.id,
    )
    db.add(event)
    db.commit()
    return RedirectResponse(url=f"/admin/events/{event.id}", status_code=303)


@router.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail(
    event_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = db.scalar(_event_query().where(Event.id == event_id))
    if not event:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "admin/event_detail.html",
        {"user": user, "event": event, "error": None},
    )


@router.post("/events/{event_id}/update")
def update_event(
    event_id: str,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(""),
    airport_code: str = Form(""),
    airport_name: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    map_center_latitude: float = Form(...),
    map_center_longitude: float = Form(...),
    default_zoom: int = Form(...),
    event_radius_nm: float = Form(...),
    return_radius_nm: float = Form(...),
    arrival_hold_seconds: int = Form(...),
    is_published: bool = Form(False),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404)
    event.name = name
    event.slug = slug
    event.description = description or None
    event.airport_code = airport_code or None
    event.airport_name = airport_name or None
    event.latitude = latitude
    event.longitude = longitude
    event.map_center_latitude = map_center_latitude
    event.map_center_longitude = map_center_longitude
    event.default_zoom = default_zoom
    event.event_radius_nm = event_radius_nm
    event.return_radius_nm = return_radius_nm
    event.arrival_hold_seconds = arrival_hold_seconds
    event.is_published = is_published
    event.is_active = is_active
    db.commit()
    return RedirectResponse(url=f"/admin/events/{event.id}", status_code=303)


@router.post("/events/{event_id}/delete")
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404)
    db.delete(event)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/events/{event_id}/aircraft")
def add_aircraft(
    event_id: str,
    tail_number: str = Form(...),
    display_name: str = Form(""),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    aircraft = EventAircraft(
        event_id=event_id,
        tail_number=tail_number.upper(),
        display_name=display_name or None,
    )
    db.add(aircraft)
    db.commit()
    return RedirectResponse(url=f"/admin/events/{event_id}", status_code=303)


@router.post("/aircraft/{aircraft_id}/delete")
def delete_aircraft(
    aircraft_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    aircraft = db.get(EventAircraft, aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404)
    event_id = aircraft.event_id
    db.delete(aircraft)
    db.commit()
    return RedirectResponse(url=f"/admin/events/{event_id}", status_code=303)


@router.post("/aircraft/{aircraft_id}/state")
def update_aircraft_state(
    aircraft_id: str,
    state: AircraftState = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    aircraft = db.get(EventAircraft, aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404)
    record_state_change(
        db,
        aircraft,
        state,
        StateSource.MANUAL,
        reason="Manual admin update",
        changed_by_user_id=user.id,
    )
    db.commit()
    return RedirectResponse(url=f"/admin/events/{aircraft.event_id}", status_code=303)


@router.post("/aircraft/{aircraft_id}/passengers")
def add_passenger(
    aircraft_id: str,
    passenger_name: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    aircraft = db.scalar(
        select(EventAircraft)
        .where(EventAircraft.id == aircraft_id)
        .options(
            selectinload(EventAircraft.passenger_assignments),
            selectinload(EventAircraft.tracks),
        )
    )
    if not aircraft:
        raise HTTPException(status_code=404)
    try:
        enqueue_passenger(db, aircraft, passenger_name)
        db.commit()
    except QueueLimitExceededError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/admin/events/{aircraft.event_id}", status_code=303)


@router.post("/aircraft/{aircraft_id}/passengers/{assignment_id}/activate")
def activate_aircraft_passenger(
    aircraft_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    aircraft = db.scalar(
        select(EventAircraft)
        .where(EventAircraft.id == aircraft_id)
        .options(
            selectinload(EventAircraft.passenger_assignments),
            selectinload(EventAircraft.tracks),
        )
    )
    if not aircraft:
        raise HTTPException(status_code=404)
    assignment = next((item for item in aircraft.passenger_assignments if item.id == assignment_id), None)
    if not assignment:
        raise HTTPException(status_code=404)
    activate_passenger(db, aircraft, assignment, datetime.utcnow())
    db.commit()
    return RedirectResponse(url=f"/admin/events/{aircraft.event_id}", status_code=303)


@router.post("/aircraft/{aircraft_id}/passengers/{assignment_id}/cancel")
def cancel_aircraft_passenger(
    aircraft_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    aircraft = db.scalar(
        select(EventAircraft)
        .where(EventAircraft.id == aircraft_id)
        .options(selectinload(EventAircraft.passenger_assignments))
    )
    if not aircraft:
        raise HTTPException(status_code=404)
    assignment = next((item for item in aircraft.passenger_assignments if item.id == assignment_id), None)
    if not assignment:
        raise HTTPException(status_code=404)
    if assignment.status == PassengerAssignmentStatus.CURRENT:
        raise HTTPException(status_code=400, detail="Current passenger cannot be cancelled.")
    removed_position = assignment.queue_position
    assignment.status = PassengerAssignmentStatus.CANCELLED
    for queued in aircraft.passenger_assignments:
        if queued.status == PassengerAssignmentStatus.QUEUED and queued.queue_position > removed_position:
            queued.queue_position -= 1
    db.commit()
    return RedirectResponse(url=f"/admin/events/{aircraft.event_id}", status_code=303)


@router.post("/events/{event_id}/simulate-observation")
def simulate_observation(
    event_id: str,
    tail_number: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    is_airborne: bool = Form(False),
    altitude_ft: int | None = Form(None),
    ground_speed_kt: int | None = Form(None),
    heading_deg: int | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    event = db.scalar(
        _event_query().where(Event.id == event_id)
    )
    if not event:
        raise HTTPException(status_code=404)
    aircraft = next((item for item in event.aircraft if item.tail_number == tail_number.upper()), None)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Tracked aircraft not found for this event.")
    process_observation(
        db,
        event,
        aircraft,
        Observation(
            tail_number=tail_number.upper(),
            latitude=latitude,
            longitude=longitude,
            observed_at=datetime.utcnow(),
            is_airborne=is_airborne,
            altitude_ft=altitude_ft,
            ground_speed_kt=ground_speed_kt,
            heading_deg=heading_deg,
            provider="simulation",
        ),
    )
    db.commit()
    return RedirectResponse(url=f"/admin/events/{event_id}", status_code=303)
