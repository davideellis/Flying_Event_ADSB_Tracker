"""create initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-30 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    aircraft_state = sa.Enum("IDLE", "BOARDING", "TAXIING", "FLYING", "ARRIVED", name="aircraftstate")
    state_source = sa.Enum("MANUAL", "AUTOMATIC", "SYSTEM", name="statesource")
    passenger_status = sa.Enum("QUEUED", "CURRENT", "COMPLETED", "CANCELLED", name="passengerassignmentstatus")
    track_status = sa.Enum("CURRENT", "ARCHIVED", name="trackstatus")

    bind = op.get_bind()
    aircraft_state.create(bind, checkfirst=True)
    state_source.create(bind, checkfirst=True)
    passenger_status.create(bind, checkfirst=True)
    track_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("airport_code", sa.String(length=16), nullable=True),
        sa.Column("airport_name", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("map_center_latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("map_center_longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("default_zoom", sa.Integer(), nullable=False),
        sa.Column("event_radius_nm", sa.Numeric(8, 2), nullable=False),
        sa.Column("return_radius_nm", sa.Numeric(8, 2), nullable=False),
        sa.Column("arrival_hold_seconds", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "event_aircraft",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=36), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("tail_number", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("manual_state", aircraft_state, nullable=False),
        sa.Column("effective_state", aircraft_state, nullable=False),
        sa.Column("state_source", state_source, nullable=False),
        sa.Column("current_passenger_assignment_id", sa.String(length=36), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("last_seen_longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("last_seen_altitude_ft", sa.Integer(), nullable=True),
        sa.Column("last_seen_ground_speed_kt", sa.Integer(), nullable=True),
        sa.Column("last_seen_heading_deg", sa.Integer(), nullable=True),
        sa.Column("last_seen_is_airborne", sa.Boolean(), nullable=True),
        sa.Column("arrival_candidate_since", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tail_number", name="uq_event_aircraft_tail_number"),
        sa.UniqueConstraint("event_id", "tail_number", name="uq_event_aircraft_event_tail_number"),
    )
    op.create_table(
        "passenger_assignments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_aircraft_id", sa.String(length=36), sa.ForeignKey("event_aircraft.id"), nullable=False),
        sa.Column("passenger_name", sa.String(length=255), nullable=False),
        sa.Column("queue_position", sa.Integer(), nullable=False),
        sa.Column("status", passenger_status, nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "aircraft_state_history",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_aircraft_id", sa.String(length=36), sa.ForeignKey("event_aircraft.id"), nullable=False),
        sa.Column("from_state", aircraft_state, nullable=True),
        sa.Column("to_state", aircraft_state, nullable=False),
        sa.Column("source", state_source, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "tracks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_aircraft_id", sa.String(length=36), sa.ForeignKey("event_aircraft.id"), nullable=False),
        sa.Column("passenger_assignment_id", sa.String(length=36), sa.ForeignKey("passenger_assignments.id"), nullable=True),
        sa.Column("status", track_status, nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "track_points",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("track_id", sa.String(length=36), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("altitude_ft", sa.Integer(), nullable=True),
        sa.Column("ground_speed_kt", sa.Integer(), nullable=True),
        sa.Column("heading_deg", sa.Integer(), nullable=True),
        sa.Column("is_airborne", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("track_points")
    op.drop_table("tracks")
    op.drop_table("aircraft_state_history")
    op.drop_table("passenger_assignments")
    op.drop_table("event_aircraft")
    op.drop_table("events")
    op.drop_table("password_reset_tokens")
    op.drop_table("users")
