# Feature Plan

## Delivery Strategy

Build v1 in thin vertical slices so the system becomes usable early while preserving room for iteration.

The recommended order is:
1. Foundation and scaffolding
2. Authentication and admin management
3. Event and aircraft configuration
4. Passenger queue management
5. Public event viewing
6. ADS-B ingestion and automation
7. Archived tracks and polish
8. Terraform and deployment hardening

## Phase 1: Foundation

Goals:
- Choose the implementation stack
- Scaffold frontend, backend, database migrations, and test tooling
- Establish repository conventions
- Add Terraform root structure in `terraform/`
- Set up linting, formatting, CI, and baseline test commands

Deliverables:
- App skeleton with clear public/admin separation
- Database migration framework
- Test runner configuration
- Initial README setup section
- Terraform skeleton and usage notes

Testing focus:
- Smoke tests for app boot
- Unit tests for initial domain utility functions
- Integration test harness setup for database-backed flows

## Phase 2: Authentication and Admin Management

Goals:
- Admin login with email/password
- Password reset flow
- Admin user creation and removal

Deliverables:
- Login page and authenticated session flow
- Password reset request and reset completion flow
- Admin user management UI/API

Testing focus:
- Unit tests for auth helpers and token handling
- Integration tests for login, logout, password reset, and admin creation/removal
- Authorization tests ensuring public users cannot access admin routes

## Phase 3: Event and Aircraft Configuration

Goals:
- Create and edit events
- Configure map defaults, airport position, event radius, return radius, and arrival hold time
- Add and manage tracked aircraft tail numbers
- Edit aircraft states manually
- Publish/unpublish and activate/deactivate events

Deliverables:
- Admin event list and event editor
- Aircraft management UI and APIs
- State update controls

Testing focus:
- Unit tests for event validation and state input validation
- Integration tests for event CRUD, aircraft CRUD, state override, and live event editing

## Phase 4: Passenger Queue Management

Goals:
- Manage up to 5 passengers per aircraft
- Activate a passenger assignment
- Archive the previous track and create a new current track when passenger changes

Deliverables:
- Passenger queue UI and APIs
- Domain service for assignment activation
- Current vs archived track model in place

Testing focus:
- Unit tests for queue size rules, ordering, activation, and archival behavior
- Integration tests for queue workflows and public redaction of passenger names

## Phase 5: Public Event Viewing

Goals:
- Public event list
- Public direct event page by slug
- Aircraft list and map display
- Toggle between tracked aircraft only and all aircraft in area

Deliverables:
- Public event directory page
- Event detail page with map and aircraft details
- Event selection and direct-link routing

Testing focus:
- Integration tests for public event visibility rules
- End-to-end smoke test for viewing a published event

## Phase 6: ADS-B Ingestion and Automation

Goals:
- Introduce ADS-B provider abstraction
- Implement first provider adapter
- Poll only active events every 10 seconds
- Auto-detect `Flying` and `Arrived`
- Persist track points and latest aircraft position

Deliverables:
- Background worker/poller
- Provider adapter interface and first implementation
- Live update API responses
- Arrival hold-time logic

Testing focus:
- Unit tests for provider normalization, geofence detection, and state automation logic
- Integration tests simulating ADS-B observations and asserting resulting state changes
- Failure-handling tests for provider timeouts and malformed responses

## Phase 7: Archived Tracks and UX Polish

Goals:
- Show archived tracks after events
- Preserve current track separately from prior passenger tracks
- Smooth marker motion client-side
- Improve admin usability and validation

Deliverables:
- Archived track rendering on public pages
- Client interpolation logic for smoother movement
- Better loading/error states

Testing focus:
- Unit tests for interpolation helpers where practical
- Integration tests for archived track retrieval and visibility
- Small end-to-end regression suite for top workflows

## Phase 8: Terraform and Deployment Hardening

Goals:
- Codify Lightsail infrastructure in Terraform
- Add deployment documentation
- Add backup and recovery guidance
- Add monitoring and health checks appropriate for v1

Deliverables:
- Terraform-managed Lightsail instance and supporting resources
- Deployment runbook
- Backup strategy documentation
- Health endpoint and operational notes

Testing focus:
- Terraform validation and formatting in CI
- Deployment smoke test checklist
- Application health check verification

## Testing Strategy

## Unit tests

Use unit tests heavily for domain logic that is easy to break:
- state transition rules
- geofence calculations
- arrival hold logic
- passenger queue rules
- track archival behavior
- ADS-B provider normalization

## Integration tests

Use integration tests for workflow confidence:
- authentication flows
- event CRUD
- aircraft CRUD
- passenger activation
- automatic `Flying` detection
- automatic `Arrived` detection
- public/private response shaping

These should run against a real test database.

## End-to-end tests

Keep these small and focused on high-risk user journeys:
- admin login
- create or edit an event
- activate an event
- assign a passenger
- view a published event publicly

## Coverage guidance

The goal is not to maximize coverage percentage blindly. The goal is to cover the rules most likely to break live event operations.

Strong candidates for mandatory automated coverage:
- anything that changes aircraft state
- anything that archives or creates tracks
- anything that filters public vs admin data
- anything that translates third-party ADS-B data into domain actions

## Terraform Guidance

Terraform must live in its own dedicated directory.

Recommended near-term structure:
- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/outputs.tf`
- `terraform/providers.tf`
- `terraform/README.md`

If the infrastructure grows, expand to:
- `terraform/modules/`
- `terraform/environments/dev/`
- `terraform/environments/prod/`

## Suggested Stack Decision Criteria

Before implementation, pick a stack that makes the following easy:
- server-rendered or hybrid frontend/admin pages
- secure session-based auth or well-supported token auth
- PostgreSQL migrations
- background job or polling worker support
- strong unit and integration testing story
- simple deployment on a single VM

Two likely good-fit directions are:
- Node.js with a full-stack framework and PostgreSQL
- Python with a full-stack framework and PostgreSQL

Either can work. Choose the one that best fits team familiarity and deployment simplicity.

## Definition of Done for Early Milestones

A phase is only complete when:
- behavior works end-to-end
- automated tests exist for the critical logic in that phase
- README and relevant docs are updated
- operational assumptions are documented where needed