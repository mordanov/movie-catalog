import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот для каталога фильмов.\n\n"
        "Команды:\n"
        "/add — добавить фильм (или просто отправь название)\n"
        "/list — список каталога\n"
        "/find <текст> — поиск\n"
        "/random — случайный фильм\n"
        "/stats — статистика\n"
        "/watched <название> — отметить как просмотрено\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Команды бота:</b>\n\n"
        "<b>Добавление:</b>\n"
        "/add &lt;название&gt; — добавить по названию\n"
        "Отправь фото скриншота — добавить по скриншоту\n\n"
        "<b>Просмотр:</b>\n"
        "/list [category] — список\n"
        "/find &lt;текст&gt; — поиск\n"
        "/random [category] — случайный\n\n"
        "<b>Управление:</b>\n"
        "/watched, /watching, /unwatched &lt;название&gt;\n"
        "/delete &lt;название&gt;\n"
        "/edit &lt;название&gt;\n\n"
        "<b>Админ:</b>\n"
        "/adduser /removeuser /users\n"
        "/stats — статистика каталога",
        parse_mode="HTML",
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/stats")
    if resp.status_code != 200:
        await message.answer("Ошибка получения статистики.")
        return
    data = resp.json()
    total = data.get("total", 0)
    by_cat = data.get("by_category", {})
    by_status = data.get("by_watched_status", {})

    lines = [f"<b>Всего:</b> {total}"]
    if by_cat:
        lines.append("\n<b>По категориям:</b>")
        labels = {
            "cartoon": "Мультфильмы", "family_movie": "Семейные фильмы",
            "adult_movie": "Взрослые фильмы", "kids_series": "Детские сериалы",
            "adult_series": "Взрослые сериалы",
        }
        for k, v in by_cat.items():
            lines.append(f"  {labels.get(k, k)}: {v}")
    if by_status:
        lines.append("\n<b>По статусу:</b>")
        slabels = {"not_watched": "Не смотрели", "watching": "Смотрим", "watched": "Просмотрено"}
        for k, v in by_status.items():
            lines.append(f"  {slabels.get(k, k)}: {v}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("random"))
async def cmd_random(message: Message):
    args = (message.text or "").split(maxsplit=1)
    params = {}
    if len(args) > 1:
        params["category"] = args[1].strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media/random", params=params)

    if resp.status_code == 404:
        await message.answer("Ничего не найдено в каталоге.")
        return
    if resp.status_code != 200:
        await message.answer(f"Ошибка: {resp.status_code}")
        return

    m = resp.json()
    title = m.get("title_ru") or m.get("title", "")
    year = m.get("year", "")
    status_emoji = {"not_watched": "👀", "watching": "▶️", "watched": "✅"}.get(m.get("watched_status", ""), "")
    await message.answer(f"{status_emoji} <b>{title}</b> ({year})", parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.")
