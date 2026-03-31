from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models import AircraftState, Event, EventAircraft
from app.services.adsb import AdsbProvider, AreaQuery, Observation
from app.services.poller import poll_active_events_once
from app.services.providers import HttpAdsbProvider


class FakeProvider(AdsbProvider):
    name = "fake"

    def __init__(self, observations):
        self.observations = observations

    async def fetch_area(self, query: AreaQuery):
        return self.observations


def test_http_provider_normalizes_adsb_like_payload():
    provider = HttpAdsbProvider()
    observations = provider._normalize_payload(
        {
            "now": 1_700_000_100,
            "ac": [
                {
                    "r": "N12345",
                    "lat": 41.5,
                    "lon": -88.1,
                    "seen_pos": 5,
                    "alt_baro": 2500,
                    "gs": 110,
                    "track": 180,
                    "air_ground": "air",
                }
            ],
        }
    )

    assert len(observations) == 1
    assert observations[0].tail_number == "N12345"
    assert observations[0].is_airborne is True
    assert observations[0].ground_speed_kt == 110


@pytest.mark.asyncio
async def test_poll_active_events_once_processes_tracked_aircraft(session):
    event = Event(
        name="Worker Demo",
        slug="worker-demo",
        latitude=41.978611,
        longitude=-87.904724,
        map_center_latitude=41.978611,
        map_center_longitude=-87.904724,
        default_zoom=11,
        event_radius_nm=15,
        return_radius_nm=2,
        arrival_hold_seconds=120,
        is_active=True,
    )
    aircraft = EventAircraft(event=event, tail_number="N12345")
    session.add_all([event, aircraft])
    session.commit()

    provider = FakeProvider(
        [
            Observation(
                tail_number="N12345",
                latitude=41.99,
                longitude=-87.90,
                observed_at=datetime.utcnow(),
                is_airborne=True,
                altitude_ft=2000,
                provider="fake",
            ),
            Observation(
                tail_number="N99999",
                latitude=41.99,
                longitude=-87.90,
                observed_at=datetime.utcnow() + timedelta(seconds=1),
                is_airborne=True,
                altitude_ft=2000,
                provider="fake",
            ),
        ]
    )

    processed = await poll_active_events_once(provider, session)
    session.refresh(aircraft)

    assert processed == 1
    assert aircraft.effective_state == AircraftState.FLYING
    assert aircraft.last_seen_altitude_ft == 2000
