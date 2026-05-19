"""Entry point — runs the Telegram bot (long-polling) and FastAPI server concurrently."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

import uvicorn

from .api import build_app
from .config import get_settings
from .store import init_registry
from .telegram_bot import build_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("claude_comm_bot")


async def _serve() -> None:
    settings = get_settings()
    init_registry(settings.data_dir / "users.json")
    bot, dp = build_bot()
    app = build_app(bot)

    config = uvicorn.Config(
        app=app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)

    log.info("Starting Telegram polling + HTTP API on http://%s:%s", settings.host, settings.port)
    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    http_task = asyncio.create_task(server.serve())

    stop_event = asyncio.Event()

    def _request_stop(*_: object) -> None:
        log.info("Shutdown requested.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, _request_stop)

    done_task = asyncio.create_task(stop_event.wait())
    try:
        await asyncio.wait(
            [polling_task, http_task, done_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        log.info("Stopping bot and HTTP server...")
        server.should_exit = True
        await dp.stop_polling()
        for task in (polling_task, http_task):
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await task
        with suppress(Exception):
            await bot.session.close()
        log.info("Stopped.")


def run() -> None:
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
