from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.models import Event, EventAircraft
from app.services.adsb import AdsbProvider, AreaQuery
from app.services.domain import process_observation


async def poll_active_events_once(provider: AdsbProvider, db: Session) -> int:
    events = db.scalars(
        select(Event)
        .where(Event.is_active.is_(True))
        .options(selectinload(Event.aircraft).selectinload(EventAircraft.tracks))
    ).all()

    processed = 0
    for event in events:
        if not event.aircraft:
            continue
        observations = await provider.fetch_area(
            AreaQuery(
                latitude=float(event.latitude),
                longitude=float(event.longitude),
                radius_nm=float(event.event_radius_nm),
            )
        )
        tracked = {aircraft.tail_number.upper(): aircraft for aircraft in event.aircraft}
        for observation in observations:
            aircraft = tracked.get(observation.tail_number.upper())
            if not aircraft:
                continue
            process_observation(db, event, aircraft, observation)
            processed += 1
    db.commit()
    return processed


async def poll_active_events_with_session(provider: AdsbProvider, session_factory: sessionmaker) -> int:
    with session_factory() as db:
        return await poll_active_events_once(provider, db)
