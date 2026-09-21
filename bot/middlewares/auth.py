from typing import Any, Callable, Awaitable

import httpx
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from cachetools import TTLCache


class WhitelistMiddleware(BaseMiddleware):
    # ponytail: in-memory TTLCache, single instance per process; fine for one-bot one-process deployment
    def __init__(self, backend_url: str, bot_secret: str, ttl: int = 60):
        self._backend_url = backend_url
        self._bot_secret = bot_secret
        self._cache: TTLCache = TTLCache(maxsize=10_000, ttl=ttl)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        tid = user.id
        allowed = self._cache.get(tid)

        if allowed is None:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self._backend_url}/api/bot/users/{tid}",
                        headers={"X-Bot-Secret": self._bot_secret},
                        timeout=5,
                    )
                allowed = resp.status_code == 200
            except Exception:
                allowed = False
            self._cache[tid] = allowed

        if not allowed:
            if isinstance(event, Message):
                await event.answer(f"У вас нет доступа к этому боту. (Ваш id: {tid})")
            return

        return await handler(event, data)
