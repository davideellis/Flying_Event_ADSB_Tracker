from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.db import SessionLocal
from app.services.poller import poll_active_events_with_session
from app.services.providers import get_adsb_provider

logger = logging.getLogger(__name__)


async def poller_loop(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    provider = get_adsb_provider()
    while not stop_event.is_set():
        try:
            await poll_active_events_with_session(provider, SessionLocal)
        except Exception:  # pragma: no cover - operational guardrail
            logger.exception("ADSB worker iteration failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.adsb_poll_seconds)
        except TimeoutError:
            continue
