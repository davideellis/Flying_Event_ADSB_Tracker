from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import Event, EventAircraft, PassengerAssignment, PassengerAssignmentStatus, User
from app.services.adsb import Observation
from app.services.auth import verify_password


def login(client, email="admin@example.com", password="Password123!"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_public_event_json_hides_passenger_names(client, session, seeded_event):
    response = client.get(f"/api/public/events/{seeded_event.slug}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["event"]["slug"] == seeded_event.slug
    assert "current_passenger_name" not in response.text


def test_public_event_json_can_show_current_passenger_name_when_enabled(client, session, seeded_event):
    aircraft = session.scalar(select(EventAircraft).where(EventAircraft.event_id == seeded_event.id))
    assignment = PassengerAssignment(
        event_aircraft_id=aircraft.id,
        passenger_name="Aviator Kid",
        queue_position=1,
        status=PassengerAssignmentStatus.CURRENT,
    )
    aircraft.current_passenger_assignment = assignment
    seeded_event.show_passenger_name_public = True
    session.add(assignment)
    session.commit()

    response = client.get(f"/api/public/events/{seeded_event.slug}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["event"]["show_passenger_name_public"] is True
    assert payload["aircraft"][0]["current_passenger_name"] == "Aviator Kid"


def test_public_event_traffic_endpoint_returns_payload(client, seeded_event, monkeypatch):
    class FakeProvider:
        name = "fake"

        async def fetch_area(self, query):
            return [
                Observation(
                    tail_number="N13579",
                    latitude=41.99,
                    longitude=-87.90,
                    observed_at=datetime.utcnow(),
                    is_airborne=True,
                    altitude_ft=2500,
                    ground_speed_kt=118,
                    heading_deg=142,
                    provider="fake",
                )
            ]

    monkeypatch.setattr("app.routers.public.get_adsb_provider", lambda: FakeProvider())
    response = client.get(f"/api/public/events/{seeded_event.slug}/traffic")

    assert response.status_code == 200
    payload = response.json()
    assert "traffic" in payload
    assert set(payload["traffic"][0].keys()) >= {
        "tail_number",
        "latitude",
        "longitude",
        "altitude_ft",
        "ground_speed_kt",
        "heading_deg",
        "is_airborne",
        "observed_at",
    }


def test_admin_can_create_event_after_login(client, session, seeded_admin):
    login_response = login(client)
    assert login_response.status_code == 303

    response = client.post(
        "/admin/events",
        data={
            "name": "Challenge Air Demo",
            "slug": "challenge-air-demo",
            "airport_code": "KADS",
            "airport_name": "Addison",
            "latitude": 32.968559,
            "longitude": -96.836449,
            "default_zoom": 11,
            "event_radius_nm": 12,
            "return_radius_nm": 2,
            "arrival_hold_seconds": 90,
            "is_published": "true",
            "is_active": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert any(event.slug == "challenge-air-demo" for event in session.query(Event).all())


def test_admin_can_create_event_from_airport_identifier(client, session, seeded_admin):
    login_response = login(client)
    assert login_response.status_code == 303

    response = client.post(
        "/admin/events",
        data={
            "name": "Addison Identifier Demo",
            "slug": "addison-identifier-demo",
            "airport_code": "KADS",
            "airport_name": "",
            "latitude": "",
            "longitude": "",
            "default_zoom": 11,
            "event_radius_nm": 12,
            "return_radius_nm": 2,
            "arrival_hold_seconds": 90,
            "is_published": "true",
            "is_active": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    event = session.scalar(select(Event).where(Event.slug == "addison-identifier-demo"))
    assert event is not None
    assert event.airport_name == "Addison Airport"
    assert float(event.latitude) == 32.968556
    assert float(event.longitude) == -96.836444
    assert float(event.map_center_latitude) == 32.968556
    assert float(event.map_center_longitude) == -96.836444


def test_admin_can_update_event_after_login(client, session, seeded_admin, seeded_event):
    login(client)

    response = client.post(
        f"/admin/events/{seeded_event.id}/update",
        data={
            "name": "Updated Event",
            "slug": seeded_event.slug,
            "description": "Updated description",
            "airport_code": seeded_event.airport_code,
            "airport_name": seeded_event.airport_name,
            "latitude": seeded_event.latitude,
            "longitude": seeded_event.longitude,
            "map_center_latitude": seeded_event.map_center_latitude,
            "map_center_longitude": seeded_event.map_center_longitude,
            "default_zoom": seeded_event.default_zoom,
            "event_radius_nm": seeded_event.event_radius_nm,
            "return_radius_nm": seeded_event.return_radius_nm,
            "arrival_hold_seconds": seeded_event.arrival_hold_seconds,
            "is_published": "true",
            "is_active": "true",
            "show_passenger_name_public": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    session.refresh(seeded_event)
    assert seeded_event.name == "Updated Event"
    assert seeded_event.show_passenger_name_public is True


def test_admin_can_update_event_from_airport_identifier(client, session, seeded_admin, seeded_event):
    login(client)

    response = client.post(
        f"/admin/events/{seeded_event.id}/update",
        data={
            "name": "Identifier Update Event",
            "slug": seeded_event.slug,
            "description": seeded_event.description or "",
            "airport_code": "KADS",
            "airport_name": "",
            "latitude": "",
            "longitude": "",
            "map_center_latitude": "",
            "map_center_longitude": "",
            "default_zoom": seeded_event.default_zoom,
            "event_radius_nm": seeded_event.event_radius_nm,
            "return_radius_nm": seeded_event.return_radius_nm,
            "arrival_hold_seconds": seeded_event.arrival_hold_seconds,
            "is_published": "true",
            "is_active": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    session.refresh(seeded_event)
    assert seeded_event.airport_code == "KADS"
    assert seeded_event.airport_name == "Addison Airport"
    assert float(seeded_event.latitude) == 32.968556
    assert float(seeded_event.longitude) == -96.836444


def test_event_admin_pages_are_split_by_workflow(client, seeded_admin, seeded_event):
    login(client)

    operations = client.get(f"/admin/events/{seeded_event.id}/operations")
    configuration = client.get(f"/admin/events/{seeded_event.id}/configuration")
    diagnostics = client.get(f"/admin/events/{seeded_event.id}/diagnostics")

    assert operations.status_code == 200
    assert configuration.status_code == 200
    assert diagnostics.status_code == 200
    assert "Live Aircraft Management" in operations.text
    assert "Event Configuration" in configuration.text
    assert "Simulation" in diagnostics.text


def test_admin_can_update_tracked_aircraft_from_configuration_page(client, session, seeded_admin, seeded_event):
    aircraft = session.scalar(select(EventAircraft).where(EventAircraft.event_id == seeded_event.id))
    login(client)

    response = client.post(
        f"/admin/aircraft/{aircraft.id}/update",
        data={"tail_number": "N777DX", "display_name": "Dispatcher One"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    session.refresh(aircraft)
    assert aircraft.tail_number == "N777DX"
    assert aircraft.display_name == "Dispatcher One"


def test_admin_can_queue_and_activate_passenger(client, session, seeded_admin, seeded_event):
    aircraft = session.scalar(select(EventAircraft).where(EventAircraft.event_id == seeded_event.id))
    login(client)

    queue_response = client.post(
        f"/admin/aircraft/{aircraft.id}/passengers",
        data={"passenger_name": "Aviator Kid"},
        follow_redirects=False,
    )
    assert queue_response.status_code == 303

    session.refresh(aircraft)
    assignment = aircraft.passenger_assignments[0]

    activate_response = client.post(
        f"/admin/aircraft/{aircraft.id}/passengers/{assignment.id}/activate",
        follow_redirects=False,
    )
    assert activate_response.status_code == 303

    session.refresh(aircraft)
    assert aircraft.current_passenger_assignment_id == assignment.id


def test_admin_can_delete_other_admin_but_not_self(client, session, seeded_admin):
    other_user = User(
        email="second@example.com",
        password_hash="hash",
        display_name="Second User",
    )
    session.add(other_user)
    session.commit()

    login(client)

    delete_other = client.post(
        f"/admin/users/{other_user.id}/delete",
        follow_redirects=False,
    )
    assert delete_other.status_code == 303
    assert session.get(User, other_user.id) is None

    delete_self = client.post(
        f"/admin/users/{seeded_admin.id}/delete",
        follow_redirects=False,
    )
    assert delete_self.status_code == 400


def test_admin_can_change_admin_password(client, session, seeded_admin):
    other_user = User(
        email="second@example.com",
        password_hash="hash",
        display_name="Second User",
    )
    session.add(other_user)
    session.commit()

    login(client)

    response = client.post(
        f"/admin/users/{other_user.id}/password",
        data={"password": "NewSecret123!"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    session.refresh(other_user)
    assert verify_password("NewSecret123!", other_user.password_hash)
