import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.states import AddMedia

router = Router()
_BACKEND = settings.backend_url

CATEGORY_LABELS = {
    "cartoon": "Мультфильм",
    "family_movie": "Семейный фильм",
    "adult_movie": "Взрослый фильм",
    "kids_series": "Детский сериал",
    "adult_series": "Взрослый сериал",
}

SUBTYPE_LABELS = {
    "disney": "Disney",
    "pixar": "Pixar",
    "soviet": "Советский",
    "russian": "Российский",
    "other": "Другой",
}


def _candidate_keyboard(candidates: list[dict], show_other: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for i, c in enumerate(candidates):
        label = f"{c['title']} ({c.get('year') or '?'})"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"candidate:{i}")])
    if show_other:
        buttons.append([InlineKeyboardButton(text="Это другое", callback_data="candidate:other")])
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="candidate:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"category:{key}")]
        for key, label in CATEGORY_LABELS.items()
    ]
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="candidate:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _subtype_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"subtype:{key}")]
        for key, label in SUBTYPE_LABELS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Добавить", callback_data="confirm:yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no"),
        ]
    ])


async def _resolve_and_show(message: Message, state: FSMContext, query: str = None, image_bytes: bytes = None):
    """Call backend resolve and display candidates."""
    await message.answer("🔍 Ищу в TMDB...")

    async with httpx.AsyncClient() as client:
        if image_bytes:
            resp = await client.post(
                f"{_BACKEND}/api/resolve/screenshot",
                files={"file": ("screenshot.jpg", image_bytes, "image/jpeg")},
                timeout=30,
            )
        else:
            resp = await client.post(f"{_BACKEND}/api/resolve", json={"query": query}, timeout=15)

    if resp.status_code != 200:
        await message.answer(f"Ошибка поиска: {resp.status_code}")
        await state.clear()
        return

    candidates = resp.json()
    if not candidates:
        await message.answer("Ничего не найдено. Попробуйте другое название.")
        await state.clear()
        return

    await state.update_data(candidates=candidates)
    await state.set_state(AddMedia.showing_candidates)

    if len(candidates) == 1:
        c = candidates[0]
        text = (
            f"<b>Найдено:</b> {c['title']} ({c.get('year') or '?'})\n"
            f"{c.get('description', '')[:200]}"
        )
        await message.answer(text, reply_markup=_confirm_keyboard(), parse_mode="HTML")
        await state.update_data(selected_index=0)
    else:
        dq = candidates[0].get("disambiguation_question") or "Какой из вариантов вы имели в виду?"
        text = f"{dq}\n"
        await message.answer(text, reply_markup=_candidate_keyboard(candidates), parse_mode="HTML")


# /add command
@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    args = (message.text or "").split(maxsplit=1)
    if len(args) > 1 and args[1].strip():
        await _resolve_and_show(message, state, query=args[1].strip())
    else:
        await message.answer("Введите название фильма или сериала:")
        await state.set_state(AddMedia.waiting_title)


# Plain text when in waiting_title state
@router.message(AddMedia.waiting_title, F.text)
async def receive_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Введите название.")
        return
    await _resolve_and_show(message, state, query=title)


# Plain text messages (not in state) — treat as implicit /add
@router.message(F.text & ~F.text.startswith("/"))
async def implicit_add(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await _resolve_and_show(message, state, query=message.text.strip())


# Photo message — screenshot mode
@router.message(F.photo)
async def receive_photo(message: Message, state: FSMContext):
    await message.answer("📷 Обрабатываю скриншот...")
    photo = message.photo[-1]  # largest size
    file = await message.bot.get_file(photo.file_id)
    downloaded = await message.bot.download_file(file.file_path)
    image_bytes = downloaded.read() if hasattr(downloaded, "read") else bytes(downloaded)
    await _resolve_and_show(message, state, image_bytes=image_bytes)


# Candidate selection callback
@router.callback_query(F.data.startswith("candidate:"), AddMedia.showing_candidates)
async def on_candidate_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", 1)[1]

    if choice == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    if choice == "other":
        await state.set_state(AddMedia.waiting_title)
        await callback.message.edit_text("Введите другое название:")
        return

    idx = int(choice)
    data = await state.get_data()
    candidates = data["candidates"]
    selected = candidates[idx]
    await state.update_data(selected_index=idx)

    # Show confirmation card
    text = (
        f"<b>{selected['title']}</b> ({selected.get('year') or '?'})\n"
        f"{selected.get('description', '')[:200]}\n\n"
        f"Добавить в каталог?"
    )
    await callback.message.edit_text(text, reply_markup=_confirm_keyboard(), parse_mode="HTML")


# Confirm add (single candidate path or after candidate selection)
@router.callback_query(F.data == "confirm:yes", AddMedia.showing_candidates)
async def on_confirm_yes(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    candidates = data["candidates"]
    idx = data.get("selected_index", 0)
    selected = candidates[idx]

    # Check if category is already set (single-candidate pre-classification)
    category = selected.get("category")
    if category:
        await state.update_data(selected_category=category, selected_subtype=selected.get("cartoon_subtype"))
        await _do_confirm(callback.message, state, selected, category, selected.get("cartoon_subtype"))
    else:
        await state.set_state(AddMedia.confirming_category)
        await callback.message.edit_text(
            f"Выберите категорию для <b>{selected['title']}</b>:",
            reply_markup=_category_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "confirm:no")
async def on_confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Отменено.")


# Category selection
@router.callback_query(F.data.startswith("category:"), AddMedia.confirming_category)
async def on_category_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    category = callback.data.split(":", 1)[1]
    await state.update_data(selected_category=category)

    if category == "cartoon":
        await state.set_state(AddMedia.confirming_add)
        await callback.message.edit_text("Выберите тип мультфильма:", reply_markup=_subtype_keyboard())
    else:
        data = await state.get_data()
        candidates = data["candidates"]
        selected = candidates[data.get("selected_index", 0)]
        await _do_confirm(callback.message, state, selected, category, None)


# Subtype selection (cartoons only)
@router.callback_query(F.data.startswith("subtype:"), AddMedia.confirming_add)
async def on_subtype_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    subtype = callback.data.split(":", 1)[1]
    data = await state.get_data()
    candidates = data["candidates"]
    selected = candidates[data.get("selected_index", 0)]
    category = data.get("selected_category", "cartoon")
    await _do_confirm(callback.message, state, selected, category, subtype)


async def _do_confirm(message, state: FSMContext, candidate: dict, category: str, cartoon_subtype: str | None):
    """POST /api/media/confirm and show result."""
    await state.clear()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BACKEND}/api/media/confirm",
            json={
                "tmdb_id": candidate["tmdb_id"],
                "media_type": candidate["media_type"],
                "category": category,
                "cartoon_subtype": cartoon_subtype,
                "source": "telegram_text",
            },
            timeout=30,
        )

    if resp.status_code == 201:
        media = resp.json()
        title = media.get("title_ru") or media.get("title", "")
        year = media.get("year", "")
        cat_label = CATEGORY_LABELS.get(media.get("category", ""), media.get("category", ""))
        await message.edit_text(
            f"✅ <b>{title}</b> ({year}) добавлен!\nКатегория: {cat_label}",
            parse_mode="HTML",
        )
    else:
        await message.edit_text(f"Ошибка добавления: {resp.status_code}\n{resp.text[:200]}")
