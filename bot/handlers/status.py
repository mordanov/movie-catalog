import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url
_HEADERS = {"X-Bot-Secret": settings.bot_secret}


async def _set_status(message: Message, status: str):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"Usage: /{status.replace('_', '')} <название>")
        return
    query = args[1].strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_BACKEND}/api/media",
            params={"search": query, "page_size": 1},
            headers=_HEADERS,
        )

    if resp.status_code != 200 or not resp.json().get("items"):
        await message.answer("Не найдено.")
        return

    m = resp.json()["items"][0]
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{_BACKEND}/api/media/{m['id']}",
            json={"watched_status": status},
            headers=_HEADERS,
        )

    if resp.status_code == 200:
        title = m.get("title_ru") or m.get("title")
        labels = {"not_watched": "не просмотрено", "watching": "смотрим", "watched": "просмотрено"}
        await message.answer(f"✅ <b>{title}</b> — {labels[status]}", parse_mode="HTML")
    else:
        await message.answer(f"Ошибка: {resp.status_code}")


@router.message(Command("watched"))
async def cmd_watched(message: Message):
    await _set_status(message, "watched")


@router.message(Command("watching"))
async def cmd_watching(message: Message):
    await _set_status(message, "watching")


@router.message(Command("unwatched"))
async def cmd_unwatched(message: Message):
    await _set_status(message, "not_watched")
