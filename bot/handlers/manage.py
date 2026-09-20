import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import settings
from bot.states import DeleteConfirm, EditMedia

router = Router()
_BACKEND = settings.backend_url
_HEADERS = {"X-Bot-Secret": settings.bot_secret}


async def _search_media(query: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_BACKEND}/api/media",
            params={"search": query, "page_size": 5},
            headers=_HEADERS,
        )
    return resp.json().get("items", []) if resp.status_code == 200 else []


# ---- DELETE ----

@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /delete <название>")
        return
    query = args[1].strip()
    items = await _search_media(query)
    if not items:
        await message.answer("Ничего не найдено.")
        return

    if len(items) == 1:
        m = items[0]
        await state.set_state(DeleteConfirm.confirming)
        await state.update_data(media_id=m["id"], title=(m.get("title_ru") or m.get("title")))
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🗑 Удалить", callback_data="delete:yes"),
            InlineKeyboardButton(text="Отмена", callback_data="delete:no"),
        ]])
        await message.answer(
            f"Удалить <b>{m.get('title_ru') or m.get('title')}</b> ({m.get('year')}) из каталога?",
            reply_markup=kb, parse_mode="HTML",
        )
    else:
        buttons = [
            [InlineKeyboardButton(
                text=f"{m.get('title_ru') or m.get('title')} ({m.get('year')})",
                callback_data=f"delete_pick:{m['id']}",
            )]
            for m in items
        ]
        buttons.append([InlineKeyboardButton(text="Отмена", callback_data="delete:no")])
        await message.answer("Выберите, что удалить:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("delete_pick:"))
async def on_delete_pick(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    media_id = callback.data.split(":", 1)[1]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media/{media_id}", headers=_HEADERS)
    if resp.status_code != 200:
        await callback.message.edit_text("Не найдено.")
        return
    m = resp.json()
    await state.set_state(DeleteConfirm.confirming)
    await state.update_data(media_id=media_id, title=(m.get("title_ru") or m.get("title")))
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Удалить", callback_data="delete:yes"),
        InlineKeyboardButton(text="Отмена", callback_data="delete:no"),
    ]])
    await callback.message.edit_text(
        f"Удалить <b>{m.get('title_ru') or m.get('title')}</b> ({m.get('year')})?",
        reply_markup=kb, parse_mode="HTML",
    )


@router.callback_query(F.data == "delete:yes", DeleteConfirm.confirming)
async def on_delete_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    media_id = data["media_id"]
    title = data["title"]
    await state.clear()
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{_BACKEND}/api/media/{media_id}", headers=_HEADERS)
    if resp.status_code == 204:
        await callback.message.edit_text(f"✅ <b>{title}</b> удалён.", parse_mode="HTML")
    else:
        await callback.message.edit_text(f"Ошибка удаления: {resp.status_code}")


@router.callback_query(F.data == "delete:no")
async def on_delete_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Отменено.")


# ---- EDIT ----

EDITABLE_FIELDS = {
    "category": "Категория",
    "cartoon_subtype": "Тип мультфильма",
    "watched_status": "Статус просмотра",
    "notes": "Заметки",
    "title_ru": "Русское название",
}

CATEGORY_OPTIONS = {"cartoon": "Мультфильм", "family_movie": "Семейный", "adult_movie": "Взрослый", "kids_series": "Детский сериал", "adult_series": "Взрослый сериал"}
SUBTYPE_OPTIONS = {"disney": "Disney", "pixar": "Pixar", "soviet": "Советский", "russian": "Российский", "other": "Другой"}
STATUS_OPTIONS = {"not_watched": "Не смотрели", "watching": "Смотрим", "watched": "Просмотрено"}


@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /edit <название>")
        return
    items = await _search_media(args[1].strip())
    if not items:
        await message.answer("Ничего не найдено.")
        return
    m = items[0]
    await state.set_state(EditMedia.choosing_field)
    await state.update_data(media_id=m["id"])
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"edit_field:{key}")]
        for key, label in EDITABLE_FIELDS.items()
    ]
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="edit_field:cancel")])
    title = m.get("title_ru") or m.get("title")
    await message.answer(
        f"Что изменить в <b>{title}</b>?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("edit_field:"), EditMedia.choosing_field)
async def on_edit_field(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    field = callback.data.split(":", 1)[1]
    if field == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return
    await state.update_data(edit_field=field)

    if field == "category":
        buttons = [[InlineKeyboardButton(text=v, callback_data=f"edit_value:{k}")] for k, v in CATEGORY_OPTIONS.items()]
        await state.set_state(EditMedia.entering_value)
        await callback.message.edit_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    elif field == "cartoon_subtype":
        buttons = [[InlineKeyboardButton(text=v, callback_data=f"edit_value:{k}")] for k, v in SUBTYPE_OPTIONS.items()]
        await state.set_state(EditMedia.entering_value)
        await callback.message.edit_text("Выберите тип:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    elif field == "watched_status":
        buttons = [[InlineKeyboardButton(text=v, callback_data=f"edit_value:{k}")] for k, v in STATUS_OPTIONS.items()]
        await state.set_state(EditMedia.entering_value)
        await callback.message.edit_text("Выберите статус:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await state.set_state(EditMedia.entering_value)
        await callback.message.edit_text(f"Введите новое значение для «{EDITABLE_FIELDS[field]}»:")


@router.callback_query(F.data.startswith("edit_value:"), EditMedia.entering_value)
async def on_edit_value_button(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    value = callback.data.split(":", 1)[1]
    data = await state.get_data()
    await state.clear()
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{_BACKEND}/api/media/{data['media_id']}",
            json={data["edit_field"]: value},
            headers=_HEADERS,
        )
    if resp.status_code == 200:
        await callback.message.edit_text("✅ Обновлено.")
    else:
        await callback.message.edit_text(f"Ошибка: {resp.status_code}")


@router.message(EditMedia.entering_value, F.text)
async def on_edit_value_text(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{_BACKEND}/api/media/{data['media_id']}",
            json={data["edit_field"]: message.text.strip()},
            headers=_HEADERS,
        )
    if resp.status_code == 200:
        await message.answer("✅ Обновлено.")
    else:
        await message.answer(f"Ошибка: {resp.status_code}")
