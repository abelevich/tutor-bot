from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from src.config import settings
from src.db.repository import setup_db
from src.bot.handlers import callbacks, commands, text
from src.bot.middlewares.user import UserMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # Register routers — order matters: commands first, then callbacks, then text (catch-all)
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(text.router)

    return dp


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Starting bot in polling mode")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Starting bot in webhook mode")

    await bot.set_webhook(
        url=settings.telegram_webhook_url,
        secret_token=settings.telegram_webhook_secret,
    )

    app = web.Application()
    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.telegram_webhook_secret,
    )
    handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8443)
    await site.start()

    logger.info("Webhook server started on 0.0.0.0:8443")

    # Keep running
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    # Initialize database
    await setup_db(settings.database_path)
    logger.info("Database initialized at %s", settings.database_path)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = create_dispatcher()

    if settings.bot_mode == "webhook":
        await run_webhook(bot, dp)
    else:
        await run_polling(bot, dp)


if __name__ == "__main__":
    asyncio.run(main())
