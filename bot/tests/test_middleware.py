import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from cachetools import TTLCache


def test_ttl_cache_stores_and_expires():
    cache = TTLCache(maxsize=1000, ttl=60)
    cache[12345] = True
    assert cache[12345] is True


def test_ttl_cache_miss_returns_none():
    cache = TTLCache(maxsize=1000, ttl=60)
    assert cache.get(99999) is None


@pytest.mark.asyncio
async def test_whitelist_middleware_allows_known_user():
    """WhitelistMiddleware should allow a user found in backend and cache the result."""
    from bot.middlewares.auth import WhitelistMiddleware

    middleware = WhitelistMiddleware(backend_url="http://fake-backend")
    middleware._cache.clear()

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        # Simulate a message event
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 12345
        event.from_user.full_name = "Test User"

        handler_called = False

        async def fake_handler(evt, data):
            nonlocal handler_called
            handler_called = True

        data = {}
        await middleware(fake_handler, event, data)

    assert handler_called
    assert middleware._cache.get(12345) is True


@pytest.mark.asyncio
async def test_whitelist_middleware_blocks_unknown_user():
    """WhitelistMiddleware should block a user not found in backend (404)."""
    from bot.middlewares.auth import WhitelistMiddleware

    middleware = WhitelistMiddleware(backend_url="http://fake-backend")
    middleware._cache.clear()

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        event = MagicMock()
        event.from_user = MagicMock()
        event.from_user.id = 99999
        event.from_user.full_name = "Unknown"
        event.answer = AsyncMock()

        handler_called = False

        async def fake_handler(evt, data):
            nonlocal handler_called
            handler_called = True

        data = {}
        await middleware(fake_handler, event, data)

    assert not handler_called
