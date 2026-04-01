from __future__ import annotations

import asyncio
import logging
import signal

from app.services.worker import poller_loop

logging.basicConfig(level=logging.INFO)


async def _run() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, request_stop)

    await poller_loop(stop_event)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
