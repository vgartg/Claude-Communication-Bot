"""Application entry point: long-polling Telegram bot."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from .agents import load_registry
from .config import load_settings
from .handlers import build_router
from .runner import Runner
from .storage import Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("bot")


async def main() -> None:
    settings = load_settings()
    registry = load_registry(settings.agents_path)

    store = Store(settings.db_path)
    await store.connect()

    runner = Runner(
        cmd=settings.runner_cmd,
        default_workdir=settings.workdir,
        permission_mode=settings.permission_mode,
        timeout=settings.timeout,
    )

    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(settings, registry, store, runner))

    logger.info("Loaded %d agents. Allowed user: %s. Workdir: %s.",
                len(registry.all()), settings.allowed_user_id, settings.workdir)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await store.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
