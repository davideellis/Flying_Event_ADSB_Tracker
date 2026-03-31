from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import airportsdata


@dataclass(frozen=True)
class AirportLookupResult:
    identifier: str
    resolved_code: str
    name: str
    latitude: float
    longitude: float


@lru_cache
def _airport_indexes() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    return (
        airportsdata.load("ICAO"),
        airportsdata.load("LID"),
        airportsdata.load("IATA"),
    )


def lookup_airport(identifier: str) -> AirportLookupResult | None:
    code = identifier.strip().upper()
    if not code:
        return None

    icao, lid, iata = _airport_indexes()
    record = icao.get(code) or lid.get(code) or iata.get(code)
    if not record:
        return None

    resolved_code = record.get("icao") or record.get("lid") or record.get("iata") or code
    return AirportLookupResult(
        identifier=code,
        resolved_code=resolved_code,
        name=record["name"],
        latitude=float(record["lat"]),
        longitude=float(record["lon"]),
    )
