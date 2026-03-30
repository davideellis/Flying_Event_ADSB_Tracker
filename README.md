# Flying Event ADS-B Tracker

A low-cost web application for managing and viewing aircraft ride events such as Young Eagles and Challenge Air. The system lets admins configure events, track specific aircraft by tail number, manage passenger assignment queues, and expose a public spectator map showing aircraft state and movement.

## Current Status

This repository is in the planning and architecture phase.

The initial v1 design targets:
- A single low-cost AWS Lightsail instance
- A public read-only event viewer
- A separate admin login and management experience
- ADS-B polling only for active events
- Support for multiple events, with one airport per event
- Aircraft state automation for `Flying` and `Arrived`
- Manual passenger queue management per aircraft
- Archived passenger tracks retained after events
- Infrastructure managed with Terraform in [`terraform/`](./terraform)

## Repo Layout

- `docs/architecture.md`: Proposed v1 application and infrastructure architecture
- `docs/database-schema.md`: Proposed relational schema and state-transition rules
- `docs/feature-plan.md`: Proposed phased delivery plan, testing strategy, and implementation guidance
- `terraform/`: Terraform configuration for AWS infrastructure

## Product Summary

### Public experience

- View active or published events
- Open an event from a list or direct shareable URL
- View aircraft positions on a map
- View aircraft status such as `Idle`, `Boarding`, `Taxiing`, `Flying`, and `Arrived`
- Toggle between tracked aircraft only and all aircraft in the event area
- View archived tracks after the event, if still published

### Admin experience

- Sign in with email and password
- Reset passwords
- Create, edit, publish, unpublish, activate, and deactivate events
- Configure event area, return radius, arrival hold time, map defaults, and tracked tail numbers
- Manage aircraft manual states
- Override automatically detected states when needed
- Manage a passenger queue of up to 5 passengers per aircraft
- Add and remove admin users

## State Model

Default aircraft states:
- `Idle`
- `Boarding`
- `Taxiing`
- `Flying`
- `Arrived`

Automation rules:
- Transition to `Flying` automatically when a tracked tail number is seen airborne inside the event area
- Transition to `Arrived` automatically when the aircraft re-enters the configured airport return radius and remains there for the configured hold time
- Admins can manually override any state

## Architecture Direction

The current recommended v1 architecture is:
- One AWS Lightsail instance
- Application server, background ADS-B poller, and PostgreSQL on the same host
- OpenStreetMap-based map stack
- Polling every 10 seconds for active events only
- Client-side interpolation for smoother aircraft movement between polls
- Terraform-managed infrastructure

See [`docs/architecture.md`](./docs/architecture.md) for details.

## Infrastructure

Terraform should remain isolated in the `terraform/` directory. As infrastructure is added, keep environment-specific values separate from shared resources and avoid mixing application code into the Terraform tree.

Planned Terraform responsibilities:
- Lightsail instance
- Static IP and DNS-related outputs where applicable
- Firewall/networking configuration
- Snapshot/backups where supported
- Secrets/bootstrap wiring as needed

## Testing Expectations

We should maintain strong automated coverage where it provides real protection.

Expected coverage areas:
- Unit tests for state transition logic, geofence logic, arrival detection, track archiving, and provider adapters
- Integration tests for API flows, authentication flows, event editing, passenger queue behavior, and ADS-B ingestion behavior
- Targeted end-to-end smoke tests for the highest-risk user journeys once the UI exists

We do not need to chase coverage for trivial UI rendering or framework boilerplate. Focus on the domain rules that can break event operations.

## README Maintenance Rule

Keep this README aligned with the actual implementation as the project evolves. When architecture, setup, or major behavior changes, update the README in the same change whenever practical.

## Next Steps

1. Choose the application stack for frontend and backend
2. Scaffold the app and test framework
3. Create the initial Terraform configuration for Lightsail
4. Implement authentication, event management, and aircraft state logic