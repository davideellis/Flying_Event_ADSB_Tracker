from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import get_settings
from app.services.adsb import AdsbProvider, AreaQuery, Observation


class StubAdsbProvider(AdsbProvider):
    name = "stub"

    async def fetch_area(self, query: AreaQuery) -> list[Observation]:
        return []


class HttpAdsbProvider(AdsbProvider):
    name = "http"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.adsb_http_base_url.rstrip("/")
        self.path_template = settings.adsb_http_area_path_template
        self.timeout_seconds = settings.adsb_http_timeout_seconds

    async def fetch_area(self, query: AreaQuery) -> list[Observation]:
        path = self.path_template.format(
            lat=query.latitude,
            lon=query.longitude,
            dist=query.radius_nm,
        )
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}{path}")
            response.raise_for_status()
        return self._normalize_payload(response.json())

    def _normalize_payload(self, payload: Any) -> list[Observation]:
        if isinstance(payload, dict):
            records = payload.get("ac") or payload.get("aircraft") or payload.get("data") or []
        elif isinstance(payload, list):
            records = payload
        else:
            records = []

        observations: list[Observation] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            tail = self._pick_tail(record)
            lat = record.get("lat")
            lon = record.get("lon")
            if not tail or lat is None or lon is None:
                continue
            seen = record.get("seen_pos")
            timestamp = record.get("now")
            observed_at = datetime.now(UTC)
            if isinstance(timestamp, (int, float)) and isinstance(seen, (int, float)):
                observed_at = datetime.fromtimestamp(timestamp - seen, tz=UTC)
            observations.append(
                Observation(
                    tail_number=tail,
                    latitude=float(lat),
                    longitude=float(lon),
                    observed_at=observed_at.replace(tzinfo=None),
                    is_airborne=self._is_airborne(record),
                    altitude_ft=self._to_int(record.get("alt_baro") or record.get("alt_geom")),
                    ground_speed_kt=self._to_int(record.get("gs") or record.get("ground_speed")),
                    heading_deg=self._to_int(record.get("track") or record.get("heading")),
                    provider=self.name,
                )
            )
        return observations

    @staticmethod
    def _is_airborne(record: dict[str, Any]) -> bool:
        if isinstance(record.get("air_ground"), str):
            return record["air_ground"].lower() == "air"
        if isinstance(record.get("alt_baro"), (int, float)):
            return float(record["alt_baro"]) > 0
        if isinstance(record.get("alt_geom"), (int, float)):
            return float(record["alt_geom"]) > 0
        return bool(record.get("is_airborne"))

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value in (None, "ground"):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def get_adsb_provider() -> AdsbProvider:
    provider_name = get_settings().adsb_provider.lower()
    if provider_name == "http":
        return HttpAdsbProvider()
    return StubAdsbProvider()
