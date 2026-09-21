import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from bot.config import settings
from bot.handlers import misc, users
from bot.middlewares.auth import WhitelistMiddleware

logging.basicConfig(level=logging.INFO)


async def bootstrap_admin(backend_url: str, admin_id: int, bot_secret: str) -> None:
    """If bot_users table is empty, add the initial admin."""
    headers = {"X-Bot-Secret": bot_secret}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{backend_url}/api/bot/users", headers=headers)
            if resp.status_code == 200 and len(resp.json()) == 0:
                await client.post(
                    f"{backend_url}/api/bot/users",
                    json={"telegram_id": admin_id, "display_name": "Admin"},
                    headers=headers,
                )
                logging.info("Bootstrapped initial admin: %s", admin_id)
        except Exception as e:
            logging.warning("Bootstrap failed: %s", e)


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Whitelist middleware on all message and callback events
    dp.message.middleware(
        WhitelistMiddleware(
            backend_url=settings.backend_url, bot_secret=settings.bot_secret
        )
    )
    dp.callback_query.middleware(
        WhitelistMiddleware(
            backend_url=settings.backend_url, bot_secret=settings.bot_secret
        )
    )

    dp.include_router(misc.router)
    dp.include_router(users.router)

    from bot.handlers import add as add_handler

    dp.include_router(add_handler.router)

    from bot.handlers import (
        list_ as list_handler,
        manage as manage_handler,
        status as status_handler,
    )

    dp.include_router(list_handler.router)
    dp.include_router(manage_handler.router)
    dp.include_router(status_handler.router)

    await bootstrap_admin(
        settings.backend_url, settings.initial_admin_telegram_id, settings.bot_secret
    )

    user_commands = [
        BotCommand(command="add", description="Добавить фильм / мультфильм / сериал"),
        BotCommand(command="list", description="Список каталога"),
        BotCommand(command="find", description="Найти по названию"),
        BotCommand(command="watched", description="Отметить просмотренным"),
        BotCommand(command="watching", description="Отметить «смотрю»"),
        BotCommand(command="unwatched", description="Убрать отметку просмотра"),
        BotCommand(command="delete", description="Удалить запись"),
        BotCommand(command="edit", description="Редактировать запись"),
        BotCommand(command="random", description="Случайная запись"),
        BotCommand(command="stats", description="Статистика каталога"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
    ]
    admin_commands = user_commands + [
        BotCommand(command="adduser", description="Добавить пользователя"),
        BotCommand(command="removeuser", description="Удалить пользователя"),
        BotCommand(command="users", description="Список пользователей"),
    ]

    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    try:
        await bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=settings.initial_admin_telegram_id),
        )
    except Exception as e:
        logging.warning(
            "Could not set admin commands (start a chat with the bot first): %s", e
        )

    logging.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
