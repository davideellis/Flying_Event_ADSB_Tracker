# Database Schema Proposal

## Overview

The application is best modeled with a relational schema in PostgreSQL. The domain is centered around events, tracked aircraft, passenger assignments, aircraft state, and track history.

This document proposes the v1 schema and the key business rules behind it.

## Core Entities

### users

Stores admin accounts.

Suggested fields:
- `id` UUID primary key
- `email` unique, not null
- `password_hash` not null
- `display_name` not null
- `is_active` boolean not null default true
- `created_at` timestamp not null
- `updated_at` timestamp not null

Notes:
- v1 uses a single admin role, so a separate roles table is not required yet
- password reset tokens can live in a separate table or be handled by the auth library if it persists them elsewhere

### password_reset_tokens

Suggested fields:
- `id` UUID primary key
- `user_id` foreign key to `users`
- `token_hash` not null
- `expires_at` timestamp not null
- `used_at` timestamp null
- `created_at` timestamp not null

### events

Represents a single ride event at one airport.

Suggested fields:
- `id` UUID primary key
- `slug` unique, not null
- `name` not null
- `description` text null
- `airport_code` null
- `airport_name` null
- `latitude` decimal not null
- `longitude` decimal not null
- `map_center_latitude` decimal not null
- `map_center_longitude` decimal not null
- `default_zoom` integer not null
- `event_radius_nm` decimal not null
- `return_radius_nm` decimal not null
- `arrival_hold_seconds` integer not null
- `is_active` boolean not null default false
- `is_published` boolean not null default false
- `starts_at` timestamp null
- `ends_at` timestamp null
- `created_by_user_id` foreign key to `users`
- `created_at` timestamp not null
- `updated_at` timestamp not null

Notes:
- `slug` supports public direct URLs
- `starts_at` and `ends_at` may be informational in v1 since activation is manual

### event_aircraft

Associates a tracked tail number with a specific event. Tail numbers are unique to one event per your rules, but modeling this as an event-scoped table keeps the domain simple.

Suggested fields:
- `id` UUID primary key
- `event_id` foreign key to `events`
- `tail_number` not null
- `display_name` null
- `manual_state` not null
- `effective_state` not null
- `state_source` not null
- `current_passenger_assignment_id` foreign key null
- `last_seen_at` timestamp null
- `last_seen_latitude` decimal null
- `last_seen_longitude` decimal null
- `last_seen_altitude_ft` integer null
- `last_seen_ground_speed_kt` integer null
- `last_seen_heading_deg` integer null
- `last_seen_is_airborne` boolean null
- `arrival_candidate_since` timestamp null
- `created_at` timestamp not null
- `updated_at` timestamp not null

Constraints:
- unique on `tail_number`
- unique on (`event_id`, `tail_number`)

Notes:
- `manual_state` is the latest admin-set state
- `effective_state` is what the UI currently shows after automation/manual override resolution
- `state_source` can be `manual` or `automatic`
- `arrival_candidate_since` supports hold-time logic for automatic arrival detection

### passenger_assignments

Represents a passenger assignment for an aircraft within an event.

Suggested fields:
- `id` UUID primary key
- `event_aircraft_id` foreign key to `event_aircraft`
- `passenger_name` not null
- `queue_position` integer not null
- `status` not null
- `activated_at` timestamp null
- `completed_at` timestamp null
- `created_at` timestamp not null
- `updated_at` timestamp not null

Suggested statuses:
- `queued`
- `current`
- `completed`
- `cancelled`

Rules:
- maximum of 5 non-completed queue entries per aircraft in v1
- only one `current` assignment per aircraft at a time
- moving to a new passenger closes the prior current track and marks the new assignment as `current`

### aircraft_state_history

Stores a history of effective state changes.

Suggested fields:
- `id` UUID primary key
- `event_aircraft_id` foreign key to `event_aircraft`
- `from_state` null
- `to_state` not null
- `source` not null
- `reason` text null
- `changed_by_user_id` foreign key null
- `created_at` timestamp not null

Sources:
- `manual`
- `automatic`
- `system`

Notes:
- Even if audit logging is not a product feature in v1, this table is still valuable for debugging state behavior

### tracks

Represents one passenger-specific or segment-specific path for an aircraft.

Suggested fields:
- `id` UUID primary key
- `event_aircraft_id` foreign key to `event_aircraft`
- `passenger_assignment_id` foreign key null
- `status` not null
- `started_at` timestamp not null
- `ended_at` timestamp null
- `archived_at` timestamp null
- `created_at` timestamp not null
- `updated_at` timestamp not null

Suggested statuses:
- `current`
- `archived`

Rules:
- only one current track per aircraft at a time
- when the current passenger changes, the current track becomes archived and a new current track is created
- archived tracks remain available after the event while published

### track_points

Stores the time-series path for a track.

Suggested fields:
- `id` bigserial primary key
- `track_id` foreign key to `tracks`
- `observed_at` timestamp not null
- `latitude` decimal not null
- `longitude` decimal not null
- `altitude_ft` integer null
- `ground_speed_kt` integer null
- `heading_deg` integer null
- `is_airborne` boolean not null
- `source` not null

Indexes:
- index on (`track_id`, `observed_at`)
- optionally index on `observed_at` for cleanup/reporting later

Notes:
- This table will grow the fastest, so keep indexes focused
- v1 volumes are still modest enough for PostgreSQL on a single instance

### adsb_observation_log

Optional but useful for debugging ingestion behavior.

Suggested fields:
- `id` bigserial primary key
- `event_id` foreign key to `events`
- `tail_number` not null
- `provider` not null
- `provider_record_id` null
- `observed_at` timestamp not null
- `payload_json` jsonb not null
- `created_at` timestamp not null

This can be omitted from the first implementation if we want to keep storage smaller.

## State Rules

### Canonical states
- `Idle`
- `Boarding`
- `Taxiing`
- `Flying`
- `Arrived`

### Manual vs effective state

Recommended rule:
- admins set `manual_state`
- system derives `effective_state`
- automatic detection can move `effective_state` to `Flying` or `Arrived`
- admin override can directly set `effective_state` too, including `Flying` and `Arrived`

A simpler implementation is also acceptable:
- store only one current state field
- record transitions in history

If we want cleaner domain behavior and fewer edge cases, keep both `manual_state` and `effective_state`.

### Automatic transition to `Flying`

Conditions:
- event is active
- aircraft belongs to the event
- matching ADS-B observation found
- aircraft is observed airborne
- observation is within the configured event radius

When true:
- set `effective_state` to `Flying`
- record history entry if the state changed

### Automatic transition to `Arrived`

Conditions:
- aircraft currently in `Flying` or manually forced airborne state
- aircraft observed within `return_radius_nm` of the event airport
- aircraft remains within that radius for at least `arrival_hold_seconds`

When true:
- set `effective_state` to `Arrived`
- record history entry
- clear arrival candidate timer fields

When false after candidacy started:
- clear `arrival_candidate_since` if the aircraft leaves the return radius before the hold is satisfied

## Public Data Exposure Rules

Public responses may include:
- event metadata
- aircraft tail number
- aircraft public state
- current and archived track geometry
- last seen timing and map positions

Public responses must not include:
- passenger names
- admin email addresses
- password or token data

## Key Constraints

Recommended v1 constraints:
- unique event slug
- unique tail number across all active event aircraft records, based on current product rule
- one current passenger assignment per aircraft
- at most 5 incomplete passenger assignments per aircraft
- one current track per aircraft

Some constraints, such as max queue size, may need service-layer enforcement rather than pure SQL constraints.

## Likely API Shapes Derived from This Schema

Examples:
- `GET /public/events`
- `GET /public/events/:slug`
- `GET /public/events/:slug/aircraft`
- `POST /admin/events`
- `PATCH /admin/events/:id`
- `POST /admin/events/:id/aircraft`
- `PATCH /admin/event-aircraft/:id/state`
- `POST /admin/event-aircraft/:id/passengers`
- `POST /admin/event-aircraft/:id/passengers/:assignmentId/activate`
- `POST /admin/users`
- `DELETE /admin/users/:id`

## Testing Priorities from the Schema

Unit tests should cover:
- event radius matching
- return radius matching
- arrival hold timing
- queue max size enforcement
- track archival on passenger activation
- state precedence rules

Integration tests should cover:
- creating an event and adding aircraft
- activating a passenger and archiving old track
- auto transition to `Flying`
- auto transition to `Arrived`
- public endpoint redaction of passenger names