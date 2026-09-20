import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers import misc, users
from bot.middlewares.auth import WhitelistMiddleware

logging.basicConfig(level=logging.INFO)


async def bootstrap_admin(backend_url: str, admin_id: int) -> None:
    """If bot_users table is empty, add the initial admin."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{backend_url}/api/bot/users")
            if resp.status_code == 200 and len(resp.json()) == 0:
                await client.post(
                    f"{backend_url}/api/bot/users",
                    json={"telegram_id": admin_id, "display_name": "Admin"},
                )
                logging.info("Bootstrapped initial admin: %s", admin_id)
        except Exception as e:
            logging.warning("Bootstrap failed: %s", e)


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Whitelist middleware on all message and callback events
    dp.message.middleware(WhitelistMiddleware(backend_url=settings.backend_url))
    dp.callback_query.middleware(WhitelistMiddleware(backend_url=settings.backend_url))

    dp.include_router(misc.router)
    dp.include_router(users.router)

    # Import add/list/manage/status routers in later tasks
    # dp.include_router(add.router)
    # dp.include_router(list_.router)
    # dp.include_router(manage.router)
    # dp.include_router(status.router)

    await bootstrap_admin(settings.backend_url, settings.initial_admin_telegram_id)
    logging.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
