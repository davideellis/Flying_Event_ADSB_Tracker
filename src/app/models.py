from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AircraftState(str, enum.Enum):
    IDLE = "Idle"
    BOARDING = "Boarding"
    TAXIING = "Taxiing"
    FLYING = "Flying"
    ARRIVED = "Arrived"


class StateSource(str, enum.Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SYSTEM = "system"


class PassengerAssignmentStatus(str, enum.Enum):
    QUEUED = "queued"
    CURRENT = "current"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrackStatus(str, enum.Enum):
    CURRENT = "current"
    ARCHIVED = "archived"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    airport_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    airport_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    map_center_latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    map_center_longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    default_zoom: Mapped[int] = mapped_column(Integer, default=11, nullable=False)
    event_radius_nm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    return_radius_nm: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    arrival_hold_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    aircraft: Mapped[list[EventAircraft]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventAircraft(Base):
    __tablename__ = "event_aircraft"
    __table_args__ = (
        UniqueConstraint("tail_number", name="uq_event_aircraft_tail_number"),
        UniqueConstraint("event_id", "tail_number", name="uq_event_aircraft_event_tail_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False)
    tail_number: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manual_state: Mapped[AircraftState] = mapped_column(
        Enum(AircraftState), default=AircraftState.IDLE, nullable=False
    )
    effective_state: Mapped[AircraftState] = mapped_column(
        Enum(AircraftState), default=AircraftState.IDLE, nullable=False
    )
    state_source: Mapped[StateSource] = mapped_column(
        Enum(StateSource), default=StateSource.MANUAL, nullable=False
    )
    current_passenger_assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("passenger_assignments.id", use_alter=True, name="fk_event_aircraft_current_passenger"),
        nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    last_seen_longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    last_seen_altitude_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_ground_speed_kt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_heading_deg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_is_airborne: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    arrival_candidate_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    event: Mapped[Event] = relationship(back_populates="aircraft")
    passenger_assignments: Mapped[list[PassengerAssignment]] = relationship(
        back_populates="event_aircraft",
        cascade="all, delete-orphan",
        foreign_keys="PassengerAssignment.event_aircraft_id",
    )
    current_passenger_assignment: Mapped[PassengerAssignment | None] = relationship(
        foreign_keys=[current_passenger_assignment_id], post_update=True
    )
    state_history: Mapped[list[AircraftStateHistory]] = relationship(
        back_populates="event_aircraft", cascade="all, delete-orphan"
    )
    tracks: Mapped[list[Track]] = relationship(back_populates="event_aircraft", cascade="all, delete-orphan")


class PassengerAssignment(Base):
    __tablename__ = "passenger_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_aircraft_id: Mapped[str] = mapped_column(ForeignKey("event_aircraft.id"), nullable=False)
    passenger_name: Mapped[str] = mapped_column(String(255), nullable=False)
    queue_position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PassengerAssignmentStatus] = mapped_column(
        Enum(PassengerAssignmentStatus), default=PassengerAssignmentStatus.QUEUED, nullable=False
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    event_aircraft: Mapped[EventAircraft] = relationship(
        back_populates="passenger_assignments", foreign_keys=[event_aircraft_id]
    )


class AircraftStateHistory(Base):
    __tablename__ = "aircraft_state_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_aircraft_id: Mapped[str] = mapped_column(ForeignKey("event_aircraft.id"), nullable=False)
    from_state: Mapped[AircraftState | None] = mapped_column(Enum(AircraftState), nullable=True)
    to_state: Mapped[AircraftState] = mapped_column(Enum(AircraftState), nullable=False)
    source: Mapped[StateSource] = mapped_column(Enum(StateSource), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    event_aircraft: Mapped[EventAircraft] = relationship(back_populates="state_history")


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_aircraft_id: Mapped[str] = mapped_column(ForeignKey("event_aircraft.id"), nullable=False)
    passenger_assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("passenger_assignments.id"), nullable=True
    )
    status: Mapped[TrackStatus] = mapped_column(
        Enum(TrackStatus), default=TrackStatus.CURRENT, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    event_aircraft: Mapped[EventAircraft] = relationship(back_populates="tracks")
    points: Mapped[list[TrackPoint]] = relationship(back_populates="track", cascade="all, delete-orphan")


class TrackPoint(Base):
    __tablename__ = "track_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    altitude_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ground_speed_kt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_deg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_airborne: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    track: Mapped[Track] = relationship(back_populates="points")
