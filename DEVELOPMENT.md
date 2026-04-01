# DEVELOPMENT.md

Agent-facing development guide for `Flying_Event_ADSB_Tracker`.

This file documents how development is expected to work in this repo, how to run and test the app, and what standards should be followed when making changes.

## Working Agreements

- `README.md` is for human-facing overview and onboarding
- `AGENTS.md` is for repo handoff and agent context
- `ARCHITECTURE.md` is for system shape and component boundaries
- `DEVELOPMENT.md` is for implementation workflow, setup, testing, and maintenance discipline

When implementation changes affect more than one of those concerns, update the relevant files together.

## Local Environment

### Requirements

- Python `3.11+`
- PowerShell is common on the main working machine

### Install

```bash
python -m pip install -e .[dev]
```

### Environment

Create a local env file:

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
- `FEAT_ADSB_WORKER_MODE`

Recommended local defaults:

- SQLite for the database
- stub ADS-B provider when working on general UI or workflow changes
- embedded worker mode for the simplest local loop

## Run Modes

### Normal local dev

```bash
python -m uvicorn app.main:app --reload
```

Open:

- public home: `http://localhost:8000/`
- admin login: `http://localhost:8000/auth/login`

### Worker modes

The app supports two worker modes:

- `embedded`
  - worker loop runs inside the FastAPI process
  - simplest local development mode
- `separate`
  - worker loop runs as a standalone process
  - mirrors production shape

Standalone worker command:

```bash
python -m app.worker_main
```

## Local Data Options

### SQLite

Best for:

- fast local development
- UI and workflow changes
- lightweight debugging

### Docker Compose + Postgres

```bash
docker compose up --build
```

Use this when:

- testing with Postgres matters
- migration behavior needs verification
- you want a closer approximation of a relational production target

## Testing

### Required checks

Run before shipping meaningful changes:

```bash
python -m pytest
python -m ruff check .
```

### Current test coverage focus

- public payload shaping
- login and admin flows
- event and aircraft workflows
- passenger queue behavior
- domain state transitions
- provider normalization
- worker and poller behavior

### Test strategy expectations

Use:

- unit tests for domain rules and provider normalization
- integration tests for admin/public workflows and route behavior

Prioritize tests for:

- anything that changes aircraft state
- anything that archives or creates tracks
- anything that exposes different public vs admin data
- anything that changes web/worker runtime behavior

## Documentation Discipline

When making changes:

- update `README.md` for human-facing changes
- update `AGENTS.md` for agent handoff or deployment reality changes
- update `ARCHITECTURE.md` for runtime/component boundary changes
- update `DEVELOPMENT.md` for workflow, setup, or testing changes

If a runtime or infrastructure change affects the system shape, also update the Mermaid architecture diagram in `README.md`.

## Terraform Workflow

Terraform lives in:

- `terraform/`

Expected checks:

```bash
terraform -chdir=terraform validate
terraform -chdir=terraform plan
```

Current note:

- the live Lightsail instance and static IP are reconciled to Terraform
- static IP attachment and public port rules are intentionally treated as operational concerns at the moment due to awkward provider behavior around already-attached resources

## Deployment Workflow

Typical production deployment pattern:

```powershell
git push origin main
ssh -i C:\Users\dave\lightsail-default.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL ubuntu@34.227.183.27 "sudo bash -lc 'git config --global --add safe.directory /opt/feat && cd /opt/feat && git fetch origin && git reset --hard origin/main && /opt/feat/.venv/bin/pip install .'"
```

Then restart services directly with one-line SSH commands.

Important:

- avoid heredoc-based restart commands from Windows when possible
- CRLF can break systemd command names like `feat\r`
- prefer direct commands or uploaded scripts normalized to Unix line endings

## Production Runtime Expectations

Current live shape:

- `feat` serves the web app
- `feat-worker` runs ADS-B polling
- `.env.web` is web-only
- `.env.worker` is worker-only

If you change service behavior, verify:

- `https://adsb.massiveweb.net/health`
- `systemctl is-active feat`
- `systemctl is-active feat-worker`

## Repo Hygiene

- keep generated state backups out of git
- keep Terraform changes isolated under `terraform/`
- avoid checking in local-only secret material
- preserve existing user changes unless explicitly asked to replace them

## Good Development Defaults

When in doubt:

- keep changes small and verifiable
- prefer domain-level fixes over template-level hacks
- add or update tests with behavior changes
- keep docs synchronized with runtime reality
