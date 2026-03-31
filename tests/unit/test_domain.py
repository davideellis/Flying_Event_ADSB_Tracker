from __future__ import annotations

from datetime import datetime, timedelta

from app.models import AircraftState, Event, EventAircraft, PassengerAssignmentStatus, StateSource
from app.services.adsb import Observation
from app.services.domain import (
    activate_passenger,
    enqueue_passenger,
    process_observation,
    record_state_change,
)
from app.services.geofence import haversine_nm, within_radius_nm


def make_event():
    return Event(
        name="Young Eagles",
        slug="young-eagles",
        latitude=41.978611,
        longitude=-87.904724,
        map_center_latitude=41.978611,
        map_center_longitude=-87.904724,
        default_zoom=11,
        event_radius_nm=15,
        return_radius_nm=2,
        arrival_hold_seconds=120,
    )


def make_aircraft(event):
    return EventAircraft(event=event, tail_number="N12345")


def test_haversine_and_radius_helpers():
    distance = haversine_nm(41.978611, -87.904724, 41.981, -87.91)
    assert distance > 0
    assert within_radius_nm(41.978611, -87.904724, 41.981, -87.91, 1)
    assert not within_radius_nm(41.978611, -87.904724, 42.5, -88.5, 5)


def test_manual_state_update_updates_effective_state(session):
    event = make_event()
    aircraft = make_aircraft(event)
    session.add_all([event, aircraft])
    session.flush()

    result = record_state_change(session, aircraft, AircraftState.BOARDING, StateSource.MANUAL)

    assert result.changed is True
    assert aircraft.manual_state == AircraftState.BOARDING
    assert aircraft.effective_state == AircraftState.BOARDING


def test_activate_passenger_archives_prior_track(session):
    event = make_event()
    aircraft = make_aircraft(event)
    session.add_all([event, aircraft])
    first = enqueue_passenger(session, aircraft, "First Rider")
    second = enqueue_passenger(session, aircraft, "Second Rider")
    session.flush()

    first_track = activate_passenger(session, aircraft, first, datetime.utcnow())
    session.flush()
    second_track = activate_passenger(
        session,
        aircraft,
        second,
        datetime.utcnow() + timedelta(minutes=20),
    )

    assert first.status == PassengerAssignmentStatus.COMPLETED
    assert first_track.status.value == "archived"
    assert second_track.status.value == "current"
    assert aircraft.current_passenger_assignment == second


def test_observation_auto_transitions_to_flying_and_arrived(session):
    event = make_event()
    aircraft = make_aircraft(event)
    session.add_all([event, aircraft])
    session.flush()

    first_seen = datetime.utcnow()
    flying_result = process_observation(
        session,
        event,
        aircraft,
        Observation(
            tail_number="N12345",
            latitude=41.99,
            longitude=-87.90,
            observed_at=first_seen,
            is_airborne=True,
            provider="test",
        ),
    )
    assert flying_result is not None
    assert aircraft.effective_state == AircraftState.FLYING

    process_observation(
        session,
        event,
        aircraft,
        Observation(
            tail_number="N12345",
            latitude=41.9788,
            longitude=-87.9047,
            observed_at=first_seen + timedelta(seconds=10),
            is_airborne=False,
            provider="test",
        ),
    )
    arrived_result = process_observation(
        session,
        event,
        aircraft,
        Observation(
            tail_number="N12345",
            latitude=41.9787,
            longitude=-87.9048,
            observed_at=first_seen + timedelta(seconds=140),
            is_airborne=False,
            provider="test",
        ),
    )

    assert arrived_result is not None
    assert aircraft.effective_state == AircraftState.ARRIVED
