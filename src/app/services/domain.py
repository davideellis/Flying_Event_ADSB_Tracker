from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    AircraftState,
    AircraftStateHistory,
    Event,
    EventAircraft,
    PassengerAssignment,
    PassengerAssignmentStatus,
    StateSource,
    Track,
    TrackPoint,
    TrackStatus,
)
from app.services.adsb import Observation
from app.services.geofence import within_radius_nm

MAX_PASSENGER_QUEUE = 5


@dataclass(slots=True)
class StateTransitionResult:
    changed: bool
    from_state: AircraftState | None
    to_state: AircraftState
    source: StateSource


class QueueLimitExceededError(ValueError):
    pass


def record_state_change(
    db: Session,
    aircraft: EventAircraft,
    to_state: AircraftState,
    source: StateSource,
    reason: str | None = None,
    changed_by_user_id: str | None = None,
) -> StateTransitionResult:
    from_state = aircraft.effective_state
    changed = from_state != to_state or aircraft.state_source != source
    aircraft.effective_state = to_state
    aircraft.state_source = source
    if source == StateSource.MANUAL:
        aircraft.manual_state = to_state
    if changed:
        db.add(
            AircraftStateHistory(
                event_aircraft=aircraft,
                from_state=from_state,
                to_state=to_state,
                source=source,
                reason=reason,
                changed_by_user_id=changed_by_user_id,
            )
        )
    return StateTransitionResult(changed=changed, from_state=from_state, to_state=to_state, source=source)


def enqueue_passenger(db: Session, aircraft: EventAircraft, passenger_name: str) -> PassengerAssignment:
    active_assignments = [
        assignment
        for assignment in aircraft.passenger_assignments
        if assignment.status in {PassengerAssignmentStatus.QUEUED, PassengerAssignmentStatus.CURRENT}
    ]
    if len(active_assignments) >= MAX_PASSENGER_QUEUE:
        raise QueueLimitExceededError("Passenger queue is limited to 5 active entries.")

    next_position = max((assignment.queue_position for assignment in active_assignments), default=0) + 1
    assignment = PassengerAssignment(
        event_aircraft=aircraft,
        passenger_name=passenger_name,
        queue_position=next_position,
        status=PassengerAssignmentStatus.QUEUED,
    )
    db.add(assignment)
    return assignment


def archive_current_track(db: Session, aircraft: EventAircraft, archived_at: datetime) -> None:
    for track in aircraft.tracks:
        if track.status == TrackStatus.CURRENT:
            track.status = TrackStatus.ARCHIVED
            track.archived_at = archived_at
            track.ended_at = archived_at


def activate_passenger(
    db: Session, aircraft: EventAircraft, assignment: PassengerAssignment, activated_at: datetime
) -> Track:
    for existing in aircraft.passenger_assignments:
        if existing.status == PassengerAssignmentStatus.CURRENT and existing.id != assignment.id:
            existing.status = PassengerAssignmentStatus.COMPLETED
            existing.completed_at = activated_at

    archive_current_track(db, aircraft, activated_at)

    assignment.status = PassengerAssignmentStatus.CURRENT
    assignment.activated_at = activated_at
    aircraft.current_passenger_assignment = assignment

    for queued in aircraft.passenger_assignments:
        if queued.status == PassengerAssignmentStatus.QUEUED and queued.queue_position > assignment.queue_position:
            queued.queue_position -= 1
    assignment.queue_position = 1

    track = Track(
        event_aircraft=aircraft,
        passenger_assignment_id=assignment.id,
        status=TrackStatus.CURRENT,
        started_at=activated_at,
    )
    db.add(track)
    return track


def get_or_create_current_track(db: Session, aircraft: EventAircraft, observed_at: datetime) -> Track:
    for track in aircraft.tracks:
        if track.status == TrackStatus.CURRENT:
            return track

    track = Track(
        event_aircraft=aircraft,
        passenger_assignment_id=aircraft.current_passenger_assignment_id,
        status=TrackStatus.CURRENT,
        started_at=observed_at,
    )
    db.add(track)
    return track


def process_observation(
    db: Session,
    event: Event,
    aircraft: EventAircraft,
    observation: Observation,
) -> StateTransitionResult | None:
    aircraft.last_seen_at = observation.observed_at
    aircraft.last_seen_latitude = observation.latitude
    aircraft.last_seen_longitude = observation.longitude
    aircraft.last_seen_altitude_ft = observation.altitude_ft
    aircraft.last_seen_ground_speed_kt = observation.ground_speed_kt
    aircraft.last_seen_heading_deg = observation.heading_deg
    aircraft.last_seen_is_airborne = observation.is_airborne

    current_track = get_or_create_current_track(db, aircraft, observation.observed_at)
    db.add(
        TrackPoint(
            track=current_track,
            observed_at=observation.observed_at,
            latitude=observation.latitude,
            longitude=observation.longitude,
            altitude_ft=observation.altitude_ft,
            ground_speed_kt=observation.ground_speed_kt,
            heading_deg=observation.heading_deg,
            is_airborne=observation.is_airborne,
            source=observation.provider,
        )
    )

    in_event_area = within_radius_nm(
        float(event.latitude),
        float(event.longitude),
        observation.latitude,
        observation.longitude,
        float(event.event_radius_nm),
    )
    in_return_area = within_radius_nm(
        float(event.latitude),
        float(event.longitude),
        observation.latitude,
        observation.longitude,
        float(event.return_radius_nm),
    )

    if observation.is_airborne and in_event_area:
        aircraft.arrival_candidate_since = None
        return record_state_change(
            db,
            aircraft,
            AircraftState.FLYING,
            StateSource.AUTOMATIC,
            reason="ADSB airborne detection in event area",
        )

    if in_return_area and aircraft.effective_state == AircraftState.FLYING:
        if aircraft.arrival_candidate_since is None:
            aircraft.arrival_candidate_since = observation.observed_at
            return None
        elapsed = (observation.observed_at - aircraft.arrival_candidate_since).total_seconds()
        if elapsed >= int(event.arrival_hold_seconds):
            aircraft.arrival_candidate_since = None
            return record_state_change(
                db,
                aircraft,
                AircraftState.ARRIVED,
                StateSource.AUTOMATIC,
                reason="ADSB arrival hold satisfied",
            )
    else:
        aircraft.arrival_candidate_since = None
    return None
