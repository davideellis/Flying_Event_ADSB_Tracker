# v1 Architecture

## Goals

The first version of this application should prioritize:
- Very low monthly cost, ideally under $10/month
- Simplicity of operations for a volunteer-run project
- Enough structure to evolve later without a full rewrite
- A clean separation between public viewing, admin workflows, and ADS-B ingestion
- The ability to swap ADS-B providers later if a public/community source changes

## Recommended Hosting Model

The recommended v1 deployment is a single AWS Lightsail instance running:
- Web frontend
- Backend API
- Background ADS-B polling worker
- PostgreSQL database
- Reverse proxy and TLS termination

This trades away high availability in favor of cost and simplicity, which matches the project goals.

## Why Lightsail for v1

Benefits:
- Predictable low monthly cost
- Simpler than a multi-service serverless architecture
- Easier to reason about for a small volunteer-operated system
- Enough capacity for the expected scale of 2 to 3 active events and around 30 tracked aircraft per event

Tradeoffs:
- Single-instance failure risk
- Manual or semi-manual scaling path
- Database shares the same host as the app in v1

These tradeoffs are acceptable for the initial version.

## High-Level Components

### 1. Frontend

Responsibilities:
- Render public event pages and admin UI
- Display map and aircraft markers
- Show aircraft status and event context
- Support event selection and direct event URLs
- Hide passenger names from public viewers
- Allow admin editing of event and aircraft data
- Smooth marker movement between ADS-B polls using client-side interpolation

Suggested behavior:
- Public pages should use read-only endpoints
- Admin pages should use authenticated endpoints
- Poll backend every 10 seconds for live event updates
- Render current passenger track separately from archived tracks

### 2. Backend API

Responsibilities:
- Authentication and session management
- Admin user management
- Event CRUD operations
- Tail-number assignment and aircraft configuration
- Passenger queue management
- Manual aircraft state changes and overrides
- Public event data responses
- Archive and retrieval of tracks

Design guidance:
- Keep public and admin routes clearly separated
- Centralize state transition rules in domain services rather than UI code
- Keep ADS-B provider logic behind an interface so providers can be replaced later

### 3. ADS-B Poller / Ingestion Worker

Responsibilities:
- Poll the ADS-B provider only for active events
- Fetch aircraft observations for event areas
- Match observations to tracked tail numbers
- Persist positions and update current tracks
- Detect transition into `Flying`
- Detect transition into `Arrived`

Polling approach:
- Run every 10 seconds while active events exist
- For each active event, request observations for the event area
- Filter to tracked tail numbers for that event
- Update observation timestamps and current position records

Automation rules:
- `Flying`: triggered when a tracked aircraft is observed airborne within the event area
- `Arrived`: triggered after the aircraft re-enters the configured return radius and remains there for the configured hold time
- Automation should work even if the prior manual state was not `Taxiing`
- Admin overrides should remain available

### 4. Database

Use PostgreSQL on the same Lightsail instance for v1.

Responsibilities:
- Store users, events, aircraft, tail numbers, passenger queues, tracks, and position samples
- Store current aircraft state and state history
- Store event configuration such as radii and hold times
- Support published vs active event visibility rules

Why PostgreSQL:
- Good fit for relational admin/event data
- Good enough for modest volumes of track samples in v1
- Easier to query archived data than a pure document model

### 5. Reverse Proxy / Web Server

Use a reverse proxy such as Nginx or Caddy for:
- TLS termination
- HTTP to HTTPS redirect
- Serving static frontend assets if needed
- Proxying API requests to the application server

Caddy is attractive for simpler TLS management. Nginx is also fine if the app stack benefits from it.

## Network and AWS Shape

### AWS Resources for v1

Keep Terraform under `terraform/` and manage at minimum:
- One Lightsail instance
- One static IP
- Firewall rules for `80` and `443`
- Optional DNS records if managed in AWS
- Optional instance snapshot configuration or documented backup procedure

### Instance Layout

Single host processes:
- Reverse proxy
- Application server
- Background worker
- PostgreSQL

Use systemd or containers on the host to keep services manageable.

## Security Model

### Public viewers
- No login required
- Can view published events
- Can view active live maps and archived tracks for published events
- Cannot view passenger names

### Admin users
- Email/password login
- Password reset flow required
- Single admin role in v1
- Admins can add and remove other admins

Minimum security controls:
- Passwords stored using a strong password hashing algorithm
- Secure session cookies or secure token handling
- CSRF protection if using cookie-based sessions
- Rate limiting on login endpoints
- Audit logging can be minimal in v1, but authentication events should still be logged operationally

## Data Flow

### Live tracking flow
1. Admin activates an event.
2. Poller begins querying the ADS-B provider for active events only.
3. Poller filters returned observations to tracked tail numbers.
4. Matching observations update aircraft current position and track samples.
5. Domain rules evaluate whether the aircraft should transition to `Flying` or `Arrived`.
6. Frontend polls the backend every 10 seconds.
7. Frontend interpolates marker positions between samples for smoother motion.

### Passenger change flow
1. Admin assigns or advances to a new passenger for an aircraft.
2. Current track is closed and archived.
3. A fresh current track is created for the new passenger.
4. Public viewers continue seeing only the current track live, while archived tracks remain available for published events.

## Map Stack

Recommended v1 map stack:
- MapLibre GL JS or Leaflet
- OpenStreetMap tiles, or another low-cost compatible provider if usage requires rate protection

Reasons:
- Low cost
- No need for expensive commercial map licensing at v1 scale
- Good fit for event-area mapping and track display

## Scalability Expectations

Expected v1 scale is modest:
- 2 to 3 active events at once
- Around 30 tracked aircraft per event
- A small number of admin users
- Public users concentrated during weekend events

The single-instance design should handle this if the implementation is efficient and polling stays bounded to active events.

## Upgrade Path

Design v1 so future changes are straightforward:
- Move PostgreSQL to a managed service later if needed
- Split worker from API if polling load grows
- Move frontend to static hosting/CDN later if traffic grows
- Replace the ADS-B provider without rewriting domain logic
- Add richer event history and reporting later

## Terraform Guidance

Keep Terraform isolated in its own directory and structure it for growth.

Suggested layout:
- `terraform/README.md`
- `terraform/environments/` for environment-specific roots if needed later
- `terraform/modules/` for reusable components once complexity justifies it

For the first cut, a simple single root module is acceptable, as long as it stays inside `terraform/`.

## Operational Guidance

Recommended v1 operations:
- Nightly PostgreSQL backup or Lightsail snapshot
- Basic health check endpoint
- Log aggregation to local files or system journal initially
- Manual recovery runbook documented in repo later

## Testing Priorities

Architecture-relevant test priorities:
- Unit tests for state transitions and geofence calculations
- Integration tests for API behavior and ADS-B ingestion workflows
- A small number of end-to-end smoke tests for admin login, event activation, and public live-map visibility

These should protect the system's core reliability without adding unnecessary maintenance overhead.