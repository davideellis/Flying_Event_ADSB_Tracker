# AGENTS.md

This file is a practical handoff for coding agents, automation frameworks, and future contributors working in this repo.

Scope of this file:

- repo orientation
- live deployment facts
- codebase entrypoints
- handoff context

For deeper system design, use [ARCHITECTURE.md](c:\Users\dave\Desktop\Dev Env\Flying_Event_ADSB_Tracker\ARCHITECTURE.md).
For development workflow and testing expectations, use [DEVELOPMENT.md](c:\Users\dave\Desktop\Dev Env\Flying_Event_ADSB_Tracker\DEVELOPMENT.md).

## Project Summary

`Flying_Event_ADSB_Tracker` is a low-cost event-tracking app for volunteer aviation ride programs such as Young Eagles and Challenge Air. It provides:

- a public read-only event viewer
- an admin experience for event setup and live dispatch workflows
- tracked-aircraft state management
- passenger queue handling
- ADS-B polling for automatic `Flying` and `Arrived` transitions

The app is intentionally optimized for cheap hosting and simple operations.

## Current Production Shape

- Host: single AWS Lightsail instance
- Reverse proxy: `nginx`
- App service: `systemd` unit named `feat`
- Worker service: `systemd` unit named `feat-worker`
- Runtime: Python virtualenv on the host
- Current production DB: SQLite on the box
- Public hostname: `https://adsb.massiveweb.net`
- Current Lightsail instance name: `flying-event-adsb-tracker-micro`
- Current Lightsail bundle: `micro_3_0`
- Current memory/swap profile: `1 GB RAM` with a `2 GB` swapfile enabled
- Production process env is expected to be split between `.env.web` and `.env.worker`

Important: the README still describes Postgres as the production target, which is the architectural direction, but the live deployed environment is currently using SQLite for simplicity and cost.

## Core Stack

- Backend: FastAPI
- ORM: SQLAlchemy 2.x
- Migrations: Alembic
- Templates: Jinja2
- Frontend behavior: vanilla JavaScript
- Map: Leaflet with OpenStreetMap tiles
- Infra as code: Terraform in `terraform/`
- Tests: `pytest`
- Lint: `ruff`

## Key Repo Areas

- `src/app/main.py`
  - app startup, router registration, runtime bootstrap
- `src/app/routers/admin.py`
  - admin pages and admin actions
- `src/app/routers/public.py`
  - public pages and public JSON endpoints
- `src/app/models.py`
  - SQLAlchemy models
- `src/app/services/domain.py`
  - domain rules, queue behavior, auto transitions
- `src/app/services/providers.py`
  - ADS-B provider abstraction
- `src/app/services/poller.py`
  - active-event polling logic
- `src/app/services/worker.py`
  - recurring in-process worker loop
- `src/app/worker_main.py`
  - standalone worker process entrypoint for production
- `src/app/templates/`
  - Jinja templates
- `src/app/static/styles.css`
  - global styling
- `src/app/static/map.js`
  - public event map logic
- `tests/integration/test_app.py`
  - app workflow tests
- `tests/unit/`
  - domain/provider/worker tests
- `docs/native-aws-option.md`
  - native AWS serverless recommendation and cost/tradeoff write-up

## Current Admin Information Architecture

- `/admin`
  - default admin landing page
  - event-centric dashboard
- `/admin/events/new`
  - dedicated event creation page
- `/admin/users`
  - dedicated user administration page
- `/admin/events/{event_id}/operations`
  - live dispatch workflow
- `/admin/events/{event_id}/configuration`
  - event setup and tracked-aircraft setup
- `/admin/events/{event_id}/diagnostics`
  - simulation and diagnostic tools

Shared top-level admin navigation lives in:

- `src/app/templates/admin/_admin_nav.html`

Shared per-event header/tabs live in:

- `src/app/templates/admin/_event_header.html`

## Behavior Rules Already Implemented

- public pages are read-only
- passenger names are hidden publicly unless explicitly enabled per event
- one airport equals one event
- one tail number belongs to one event
- `Flying` can be auto-triggered from ADS-B observation while airborne in event area
- `Arrived` can be auto-triggered after aircraft remains inside return radius for configured hold time
- admins can still manually override states
- passenger track history is archived on passenger rollover

## Local Development Commands

These are quick pointers only. The fuller development workflow lives in [DEVELOPMENT.md](c:\Users\dave\Desktop\Dev Env\Flying_Event_ADSB_Tracker\DEVELOPMENT.md).

Install:

```bash
python -m pip install -e .[dev]
```

Run app:

```bash
python -m uvicorn app.main:app --reload
```

Run tests:

```bash
python -m pytest
```

Run lint:

```bash
python -m ruff check .
```

## Deployment Notes

The local machine used recently for deployment had:

- repo path: `c:\Users\dave\Desktop\Dev Env\Flying_Event_ADSB_Tracker`
- Lightsail SSH key path: `C:\Users\dave\lightsail-default.pem`

Typical live update flow used successfully:

```powershell
git push origin main
ssh -i C:\Users\dave\lightsail-default.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL ubuntu@34.227.183.27 "sudo bash -lc 'git config --global --add safe.directory /opt/feat && cd /opt/feat && git fetch origin && git reset --hard origin/main && /opt/feat/.venv/bin/pip install .'"
ssh -i C:\Users\dave\lightsail-default.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL ubuntu@34.227.183.27 "sudo systemctl restart feat && sudo systemctl is-active feat"
```

Important operational note:

- Running restart commands through piped heredoc blocks can inject CRLF and cause `feat\\r` / `feat\\x0d` systemd errors.
- Prefer direct one-line SSH commands for restart operations.
- A manual Lightsail resize was performed by snapshotting the original `flying-event-adsb-tracker` instance, creating `flying-event-adsb-tracker-micro`, attaching the existing static IP, enabling swap, and deleting the original instance.
- Terraform has been reconciled to the live Lightsail instance name and bundle.

## Testing Expectations

When changing behavior:

- add or update unit tests when domain logic changes
- add or update integration tests when admin/public workflows change
- keep `python -m pytest` passing
- keep `python -m ruff check .` passing

## Documentation Expectations

- Keep `README.md` current when architecture, setup flow, or major user-visible behavior changes
- Keep `AGENTS.md` current when deployment reality, workflow notes, or repo handoff context changes
- Keep Terraform isolated under `terraform/`

## Good Next Targets

- verified live ADS-B provider tuning against the actual production source
- keep the dedicated worker service healthy and in sync with the web process during deploys
- improve backup/restore and snapshot runbooks
- smooth more admin UI inconsistencies as pages evolve
