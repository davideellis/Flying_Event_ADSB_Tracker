from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Event, EventAircraft, PassengerAssignmentStatus, Track, TrackStatus
from app.services.adsb import AreaQuery
from app.services.providers import get_adsb_provider

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="src/app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    events = db.scalars(
        select(Event).where(Event.is_published.is_(True)).order_by(Event.name)
    ).all()
    return templates.TemplateResponse(request, "public/index.html", {"events": events})


@router.get("/public/events", response_class=HTMLResponse)
def public_events(request: Request, db: Session = Depends(get_db)):
    events = db.scalars(
        select(Event).where(Event.is_published.is_(True)).order_by(Event.name)
    ).all()
    return templates.TemplateResponse(request, "public/index.html", {"events": events})


@router.get("/public/events/{slug}", response_class=HTMLResponse)
def public_event_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    event = db.scalar(
        select(Event)
        .where(Event.slug == slug, Event.is_published.is_(True))
        .options(
            selectinload(Event.aircraft).selectinload(EventAircraft.passenger_assignments),
            selectinload(Event.aircraft).selectinload(EventAircraft.tracks),
            selectinload(Event.aircraft).selectinload(EventAircraft.state_history),
        )
    )
    if not event:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "public/event_detail.html", {"event": event})


@router.get("/api/public/events/{slug}")
def public_event_json(slug: str, db: Session = Depends(get_db)):
    event = db.scalar(
        select(Event)
        .where(Event.slug == slug, Event.is_published.is_(True))
        .options(
            selectinload(Event.aircraft).selectinload(EventAircraft.passenger_assignments),
            selectinload(Event.aircraft).selectinload(EventAircraft.tracks).selectinload(Track.points),
        )
    )
    if not event:
        raise HTTPException(status_code=404)

    aircraft_payload = []
    for aircraft in event.aircraft:
        current_track = next(
            (track for track in aircraft.tracks if track.status == TrackStatus.CURRENT),
            None,
        )
        archived_tracks = [
            track for track in aircraft.tracks if track.status == TrackStatus.ARCHIVED
        ]
        aircraft_payload.append(
            {
                "id": aircraft.id,
                "tail_number": aircraft.tail_number,
                "display_name": aircraft.display_name,
                "state": aircraft.effective_state.value,
                "last_seen_at": aircraft.last_seen_at.isoformat() if aircraft.last_seen_at else None,
                "last_seen": {
                    "latitude": _to_float(aircraft.last_seen_latitude),
                    "longitude": _to_float(aircraft.last_seen_longitude),
                    "altitude_ft": aircraft.last_seen_altitude_ft,
                    "ground_speed_kt": aircraft.last_seen_ground_speed_kt,
                    "heading_deg": aircraft.last_seen_heading_deg,
                    "is_airborne": aircraft.last_seen_is_airborne,
                },
                "current_track": [_point_payload(point) for point in (current_track.points if current_track else [])],
                "archived_tracks": [
                    [_point_payload(point) for point in track.points]
                    for track in archived_tracks
                ],
                "has_current_passenger": any(
                    assignment.status == PassengerAssignmentStatus.CURRENT
                    for assignment in aircraft.passenger_assignments
                ),
            }
        )
    return JSONResponse(
        {
            "event": {
                "id": event.id,
                "slug": event.slug,
                "name": event.name,
                "airport_code": event.airport_code,
                "airport_name": event.airport_name,
                "latitude": float(event.latitude),
                "longitude": float(event.longitude),
                "map_center_latitude": float(event.map_center_latitude),
                "map_center_longitude": float(event.map_center_longitude),
                "default_zoom": event.default_zoom,
                "event_radius_nm": float(event.event_radius_nm),
            },
            "aircraft": aircraft_payload,
        }
    )


@router.get("/api/public/events/{slug}/traffic")
async def public_event_traffic(slug: str, db: Session = Depends(get_db)):
    event = db.scalar(select(Event).where(Event.slug == slug, Event.is_published.is_(True)))
    if not event:
        raise HTTPException(status_code=404)
    provider = get_adsb_provider()
    observations = await provider.fetch_area(
        AreaQuery(
            latitude=float(event.latitude),
            longitude=float(event.longitude),
            radius_nm=float(event.event_radius_nm),
        )
    )
    return {
        "provider": provider.name,
        "traffic": [
            {
                "tail_number": observation.tail_number,
                "latitude": observation.latitude,
                "longitude": observation.longitude,
                "is_airborne": observation.is_airborne,
                "observed_at": observation.observed_at.isoformat(),
            }
            for observation in observations
        ],
    }



def _point_payload(point) -> dict[str, float | str]:
    return {
        "lat": float(point.latitude),
        "lon": float(point.longitude),
        "observed_at": point.observed_at.isoformat(),
    }



def _to_float(value):
    return float(value) if value is not None else None
