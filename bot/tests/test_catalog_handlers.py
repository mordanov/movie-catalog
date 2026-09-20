"""Tests for /list, /find, /delete, /edit, /watched handlers."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_resp(status_code: int, body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    return r


# ---------------------------------------------------------------------------
# list_ handler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cmd_list_returns_catalog():
    from bot.handlers.list_ import cmd_list, _format_list

    items = [{"title": "Toy Story", "title_ru": "История игрушек", "year": 1995, "watched_status": "watched"}]
    fake_resp = _mock_resp(200, {"items": items, "total": 1})

    message = MagicMock()
    message.text = "/list"
    message.answer = AsyncMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fake_resp):
        await cmd_list(message)

    message.answer.assert_awaited_once()
    text = message.answer.call_args[0][0]
    assert "История игрушек" in text
    assert "всего 1" in text


@pytest.mark.asyncio
async def test_cmd_list_error():
    from bot.handlers.list_ import cmd_list

    message = MagicMock()
    message.text = "/list"
    message.answer = AsyncMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_mock_resp(500, {})):
        await cmd_list(message)

    text = message.answer.call_args[0][0]
    assert "500" in text


@pytest.mark.asyncio
async def test_cmd_find_no_query():
    from bot.handlers.list_ import cmd_find

    message = MagicMock()
    message.text = "/find"
    message.answer = AsyncMock()

    await cmd_find(message)

    text = message.answer.call_args[0][0]
    assert "Usage" in text


@pytest.mark.asyncio
async def test_cmd_find_results():
    from bot.handlers.list_ import cmd_find

    items = [{"title": "Toy Story", "title_ru": None, "year": 1995, "watched_status": "not_watched"}]
    message = MagicMock()
    message.text = "/find Toy"
    message.answer = AsyncMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_mock_resp(200, {"items": items, "total": 1})):
        await cmd_find(message)

    text = message.answer.call_args[0][0]
    assert "Toy Story" in text


@pytest.mark.asyncio
async def test_cmd_find_empty():
    from bot.handlers.list_ import cmd_find

    message = MagicMock()
    message.text = "/find xyznotfound"
    message.answer = AsyncMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_mock_resp(200, {"items": [], "total": 0})):
        await cmd_find(message)

    text = message.answer.call_args[0][0]
    assert "не найдено" in text.lower()


# ---------------------------------------------------------------------------
# manage handler — delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cmd_delete_no_arg():
    from bot.handlers.manage import cmd_delete

    message = MagicMock()
    message.text = "/delete"
    message.answer = AsyncMock()
    state = AsyncMock()

    await cmd_delete(message, state)

    text = message.answer.call_args[0][0]
    assert "Usage" in text


@pytest.mark.asyncio
async def test_cmd_delete_single_match():
    from bot.handlers.manage import cmd_delete

    items = [{"id": "abc", "title": "Toy Story", "title_ru": None, "year": 1995}]
    message = MagicMock()
    message.text = "/delete Toy Story"
    message.answer = AsyncMock()
    state = AsyncMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_mock_resp(200, {"items": items, "total": 1})):
        await cmd_delete(message, state)

    state.set_state.assert_awaited_once()
    message.answer.assert_awaited_once()
    text = message.answer.call_args[0][0]
    assert "Toy Story" in text


@pytest.mark.asyncio
async def test_on_delete_confirm_success():
    from bot.handlers.manage import on_delete_confirm

    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()

    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"media_id": "abc", "title": "Toy Story"})
    state.clear = AsyncMock()

    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock, return_value=_mock_resp(204, None)):
        await on_delete_confirm(callback, state)

    text = callback.message.edit_text.call_args[0][0]
    assert "Toy Story" in text
    assert "✅" in text


# ---------------------------------------------------------------------------
# status handler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cmd_watched_sets_status():
    from bot.handlers.status import cmd_watched

    items = [{"id": "abc", "title": "Toy Story", "title_ru": None}]
    message = MagicMock()
    message.text = "/watched Toy Story"
    message.answer = AsyncMock()

    search_resp = _mock_resp(200, {"items": items})
    patch_resp = _mock_resp(200, {"id": "abc"})

    call_count = 0

    async def mock_get(*a, **kw):
        return search_resp

    async def mock_patch(*a, **kw):
        return patch_resp

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=search_resp), \
         patch("httpx.AsyncClient.patch", new_callable=AsyncMock, return_value=patch_resp):
        await cmd_watched(message)

    text = message.answer.call_args[0][0]
    assert "Toy Story" in text
    assert "просмотрено" in text


@pytest.mark.asyncio
async def test_cmd_unwatched_no_arg():
    """Without a title arg, should operate on the most recently added item."""
    from bot.handlers.status import cmd_unwatched

    item = {"id": "abc-123", "title": "Toy Story", "title_ru": None}
    message = MagicMock()
    message.text = "/unwatched"
    message.answer = AsyncMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_mock_resp(200, {"items": [item]})), \
         patch("httpx.AsyncClient.patch", new_callable=AsyncMock, return_value=_mock_resp(200, item)):
        await cmd_unwatched(message)

    text = message.answer.call_args[0][0]
    assert "Toy Story" in text


# ---------------------------------------------------------------------------
# list_ format helper
# ---------------------------------------------------------------------------

def test_format_list_includes_emoji():
    from bot.handlers.list_ import _format_list

    items = [
        {"title": "A", "title_ru": None, "year": 2020, "watched_status": "watched"},
        {"title": "B", "title_ru": "Б", "year": 2021, "watched_status": "watching"},
    ]
    text = _format_list(items, 1, 2, 10)
    assert "✅" in text
    assert "▶️" in text
    assert "Б" in text
    assert "Страница 1" in text
