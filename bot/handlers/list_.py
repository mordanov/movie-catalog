import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url
_HEADERS = {"X-Bot-Secret": settings.bot_secret}

STATUS_EMOJI = {"not_watched": "👀", "watching": "▶️", "watched": "✅"}


def _pagination_keyboard(page: int, total: int, page_size: int, prefix: str) -> InlineKeyboardMarkup | None:
    buttons = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"{prefix}:page:{page - 1}"))
    if page * page_size < total:
        row.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"{prefix}:page:{page + 1}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def _format_list(items: list[dict], page: int, total: int, page_size: int) -> str:
    lines = [f"<b>Каталог</b> (всего {total}):"]
    for m in items:
        title = m.get("title_ru") or m.get("title", "")
        year = m.get("year", "")
        emoji = STATUS_EMOJI.get(m.get("watched_status", ""), "")
        lines.append(f"{emoji} {title} ({year})")
    lines.append(f"\nСтраница {page}")
    return "\n".join(lines)


@router.message(Command("list"))
async def cmd_list(message: Message):
    args = (message.text or "").split(maxsplit=1)
    params = {"page": 1, "page_size": 10}
    if len(args) > 1:
        params["category"] = args[1].strip()
    prefix = f"list:{params.get('category', '')}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media", params=params, headers=_HEADERS)

    if resp.status_code != 200:
        await message.answer(f"Ошибка: {resp.status_code}")
        return

    data = resp.json()
    text = _format_list(data["items"], 1, data["total"], 10)
    kb = _pagination_keyboard(1, data["total"], 10, prefix)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^list:.*:page:\d+$"))
async def on_list_page(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split(":")
    # format: list:<category>:page:<n>
    category = parts[1]
    page = int(parts[3])
    params = {"page": page, "page_size": 10}
    if category:
        params["category"] = category
    prefix = f"list:{category}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media", params=params, headers=_HEADERS)

    if resp.status_code != 200:
        await callback.message.edit_text(f"Ошибка: {resp.status_code}")
        return

    data = resp.json()
    text = _format_list(data["items"], page, data["total"], 10)
    kb = _pagination_keyboard(page, data["total"], 10, prefix)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("find"))
async def cmd_find(message: Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /find <текст поиска>")
        return
    query = args[1].strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_BACKEND}/api/media",
            params={"search": query, "page_size": 20},
            headers=_HEADERS,
        )

    if resp.status_code != 200:
        await message.answer(f"Ошибка: {resp.status_code}")
        return

    data = resp.json()
    if not data["items"]:
        await message.answer("Ничего не найдено.")
        return

    text = _format_list(data["items"], 1, data["total"], 20)
    await message.answer(text, parse_mode="HTML")
