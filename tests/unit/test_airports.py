from __future__ import annotations

from app.services.airports import lookup_airport


def test_lookup_airport_supports_icao_code():
    airport = lookup_airport("KADS")

    assert airport is not None
    assert airport.name == "Addison Airport"
    assert airport.latitude == 32.968556
    assert airport.longitude == -96.836444


def test_lookup_airport_supports_faa_lid_code():
    airport = lookup_airport("ADS")

    assert airport is not None
    assert airport.name == "Addison Airport"
    assert airport.latitude == 32.968556
    assert airport.longitude == -96.836444


def test_lookup_airport_returns_none_for_unknown_identifier():
    assert lookup_airport("ZZZZ-NOT-REAL") is None
