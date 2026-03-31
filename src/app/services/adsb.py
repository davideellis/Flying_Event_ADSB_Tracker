from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Observation:
    tail_number: str
    latitude: float
    longitude: float
    observed_at: datetime
    is_airborne: bool
    altitude_ft: int | None = None
    ground_speed_kt: int | None = None
    heading_deg: int | None = None
    provider: str = "stub"


@dataclass(slots=True)
class AreaQuery:
    latitude: float
    longitude: float
    radius_nm: float


class AdsbProvider:
    name = "base"

    async def fetch_area(self, query: AreaQuery) -> list[Observation]:
        raise NotImplementedError

    @staticmethod
    def _pick_tail(raw: dict[str, Any]) -> str | None:
        for key in ("r", "registration", "tail_number", "tail", "flight"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
        return None
