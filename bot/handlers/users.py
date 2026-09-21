import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url
_HEADERS = {"X-Bot-Secret": settings.bot_secret}


@router.message(Command("adduser"))
async def cmd_adduser(message: Message):
    """Usage: /adduser <telegram_id> [display_name]"""
    args = (message.text or "").split(maxsplit=2)[1:]
    if not args:
        await message.answer("Usage: /adduser <telegram_id> [display_name]")
        return
    try:
        telegram_id = int(args[0])
    except ValueError:
        await message.answer("telegram_id must be an integer")
        return
    display_name = args[1] if len(args) > 1 else None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BACKEND}/api/bot/users",
            json={
                "telegram_id": telegram_id,
                "display_name": display_name,
                "added_by_telegram_id": message.from_user.id,
            },
            headers=_HEADERS,
        )

    if resp.status_code == 201:
        await message.answer(f"Пользователь {telegram_id} добавлен.")
    elif resp.status_code == 409:
        await message.answer("Пользователь уже существует.")
    else:
        await message.answer(f"Ошибка: {resp.status_code}")


@router.message(Command("removeuser"))
async def cmd_removeuser(message: Message):
    """Usage: /removeuser <telegram_id>"""
    args = (message.text or "").split(maxsplit=1)[1:]
    if not args:
        await message.answer("Usage: /removeuser <telegram_id>")
        return
    try:
        telegram_id = int(args[0])
    except ValueError:
        await message.answer("telegram_id must be an integer")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{_BACKEND}/api/bot/users/{telegram_id}", headers=_HEADERS
        )

    if resp.status_code == 204:
        await message.answer(f"Пользователь {telegram_id} удалён.")
    else:
        await message.answer(f"Не найден или ошибка: {resp.status_code}")


@router.message(Command("users"))
async def cmd_users(message: Message):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/bot/users", headers=_HEADERS)

    if resp.status_code != 200:
        await message.answer("Ошибка получения списка.")
        return

    users = resp.json()
    if not users:
        await message.answer("Список пользователей пуст.")
        return

    lines = [
        f"• {u['telegram_id']} — {u.get('display_name') or 'без имени'}" for u in users
    ]
    await message.answer("Пользователи:\n" + "\n".join(lines))
