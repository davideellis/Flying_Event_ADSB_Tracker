from __future__ import annotations

from sqlalchemy import select

from app.models import Event, EventAircraft, User


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
    assert "passenger_name" not in response.text


def test_public_event_traffic_endpoint_returns_payload(client, seeded_event):
    response = client.get(f"/api/public/events/{seeded_event.slug}/traffic")

    assert response.status_code == 200
    assert "traffic" in response.json()


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
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    session.refresh(seeded_event)
    assert seeded_event.name == "Updated Event"


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
