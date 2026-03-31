# Flying Event ADS-B Tracker

A low-cost web application for managing and viewing aircraft ride events such as Young Eagles and Challenge Air. The system lets admins configure events, track specific aircraft by tail number, manage passenger assignment queues, poll ADS-B traffic for active events, and expose a public spectator map showing aircraft state and movement.

## Status

The repo now includes a broader working stack:
- FastAPI application with server-rendered public and admin pages
- SQLAlchemy models for users, events, aircraft, passengers, tracks, and state history
- Core domain logic for passenger queues, track archiving, manual overrides, and automatic `Flying`/`Arrived` transitions
- ADS-B provider abstraction with a public HTTP-compatible provider and stub provider
- Background poller loop for active events
- Initial Alembic migration
- Unit and integration tests covering domain, worker, provider normalization, and app flows
- Docker and docker-compose scaffolding for local app + Postgres
- Terraform baseline for a low-cost AWS Lightsail deployment

## Chosen Stack

- Backend: FastAPI
- Database layer: SQLAlchemy 2.x + Alembic
- Templates/UI: Jinja2 + vanilla JavaScript + Leaflet
- Password hashing: `pbkdf2_sha256` via Passlib
- Live traffic integration: pluggable ADS-B providers
- Background processing: in-process async worker loop for v1
- Production target: PostgreSQL on a single AWS Lightsail instance
- Local default: SQLite for quick setup, Postgres via Docker Compose when desired
- Infra: Terraform in [`terraform/`](./terraform)

This stack keeps deployment simple on one VM while still giving us a clean path to split the worker, move to managed Postgres, or swap ADS-B providers later.

## Current Features

### Public
- Published event list
- Direct event page by slug
- Public aircraft states
- Map with current and archived tracks
- JSON endpoint for tracked event polling
- Area-traffic JSON endpoint for the public map toggle
- Passenger names hidden from public responses

### Admin
- Email/password login
- Password reset token flow for local/dev use
- Bootstrap admin user on first startup
- Create, edit, and delete events
- Add and delete tracked aircraft
- Manually set aircraft state
- Queue, activate, and cancel passengers
- Create and remove additional admin users with basic safety checks
- Simulate aircraft observations for testing event behavior without live traffic

### Domain automation
- Transition to `Flying` automatically when a tracked aircraft is observed airborne inside the event area
- Transition to `Arrived` automatically when the aircraft stays inside the configured return radius for the configured hold time
- Manual overrides still supported

### Worker / provider
- Poll active events only
- Provider interface to keep data-source swaps isolated
- Stub provider for local testing
- HTTP-compatible provider designed for public/community ADS-B sources

## Repo Layout

- `src/app/`: FastAPI app code
- `migrations/`: Alembic migration files
- `tests/`: Unit and integration tests
- `docker-compose.yml`: local app + Postgres stack
- `Dockerfile`: container image for the app
- `docs/architecture.md`: architecture direction and hosting rationale
- `docs/database-schema.md`: data model and domain rules
- `docs/feature-plan.md`: delivery plan and testing guidance
- `terraform/`: Terraform for AWS infrastructure

## Local Setup

### Requirements
- Python 3.11+

### Install
```bash
python -m pip install -e .[dev]
```

### Configure
```bash
copy .env.example .env
```

Important settings:
- `FEAT_SECRET_KEY`
- `FEAT_DATABASE_URL`
- `FEAT_BOOTSTRAP_ADMIN_EMAIL`
- `FEAT_BOOTSTRAP_ADMIN_PASSWORD`
- `FEAT_PASSWORD_RESET_BASE_URL`
- `FEAT_ADSB_PROVIDER`
- `FEAT_ADSB_POLL_SECONDS`
- `FEAT_ADSB_HTTP_BASE_URL`
- `FEAT_ADSB_HTTP_AREA_PATH_TEMPLATE`
- `FEAT_ADSB_WORKER_ENABLED`

### Run the app
```bash
python -m uvicorn app.main:app --reload
```

Open:
- Public home: `http://localhost:8000/`
- Admin login: `http://localhost:8000/auth/login`

Default bootstrap admin comes from `.env` or the built-in defaults.

## Docker / Postgres

To run the app with Postgres locally:
```bash
docker compose up --build
```

This starts:
- app on `http://localhost:8000`
- Postgres on `localhost:5432`

The compose stack defaults to the stub ADS-B provider so local development stays predictable.

## Testing

Run tests:
```bash
python -m pytest
```

Run linting:
```bash
python -m ruff check .
```

Current automated coverage includes:
- geofence math
- state transitions
- passenger queue activation/cancellation and track archival
- provider normalization
- poller processing for active events
- public payload redaction
- admin login and core event/user/passenger workflows

## Database Notes

The app currently uses SQLAlchemy models and an initial Alembic migration.

For local development, SQLite is the default.
For production on Lightsail, we should use PostgreSQL and point `FEAT_DATABASE_URL` at it.

## ADS-B Provider Notes

The provider layer is intentionally abstracted so we can swap public/community sources later. The current HTTP provider is designed for ADSBExchange-compatible area queries and can be adapted by changing configuration rather than rewriting domain logic.

## Terraform

Terraform stays isolated under `terraform/`.

Current baseline includes:
- Lightsail instance
- Static IP
- Public ports for SSH/HTTP/HTTPS
- Optional SSH key registration
- Docker bootstrap packages via cloud-init style user data

Before applying Terraform, review bundle size and region to make sure the monthly cost stays within the target budget.

## README Maintenance Rule

Keep this README aligned with implementation changes. If the architecture, setup, stack, or major behavior changes, update the README in the same change whenever practical.

## Remaining High-Value Work

1. Wire a live ADS-B provider configuration that's verified against the exact source you want to use in production
2. Replace the in-process worker with a separately managed process or service unit for production hardening
3. Add richer event audit trails and historical admin activity if the project grows
4. Expand deployment automation and backup/restore runbooks for Lightsail
