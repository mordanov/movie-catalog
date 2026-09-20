import json
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings

# ponytail: lazy init so import succeeds without OPENAI_API_KEY set (e.g. in tests)
_client: AsyncOpenAI | None = None


def _ensure_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    return _client


_CLASSIFY_SYSTEM = """You classify movies/cartoons/series into catalog categories.
Given title, genres, description, and origin country, return JSON only:
{"category": "<kids_series|adult_series|family_movie|adult_movie|cartoon>",
 "cartoon_subtype": "<disney|pixar|soviet|russian|other|null>"}
cartoon_subtype is null if category is not cartoon."""

_EXTRACT_SYSTEM = """You extract movie/series info from a screenshot description.
Return JSON only: {"title": "<best guess title>", "year_hint": <int or null>}"""


async def translate_to_russian(text: str) -> str:
    """Translate text to Russian. Returns plain string."""
    resp = await _ensure_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Translate the following movie description to Russian. Return only the translation."},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content.strip()


async def classify_media(
    title: str,
    genres: list[str],
    description: str | None,
    origin_country: list[str],
) -> dict[str, Any]:
    """Returns {"category": ..., "cartoon_subtype": ...}"""
    user_msg = (
        f"Title: {title}\nGenres: {', '.join(genres)}\n"
        f"Description: {description or 'N/A'}\nOrigin: {', '.join(origin_country)}"
    )
    resp = await _ensure_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _CLASSIFY_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


async def extract_from_screenshot(image_bytes: bytes) -> dict[str, Any]:
    """Returns {"title": str, "year_hint": int|None}"""
    import base64
    b64 = base64.b64encode(image_bytes).decode()
    resp = await _ensure_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _EXTRACT_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What movie or series is shown?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


async def generate_disambiguation_question(candidates: list[dict]) -> str:
    """Given a list of candidate dicts, generate a clarifying question."""
    lines = "\n".join(
        f"{i+1}. {c['title']} ({c.get('year', '?')}) — {c.get('description', '')[:80]}"
        for i, c in enumerate(candidates)
    )
    resp = await _ensure_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You help a user pick the right movie from a list. Ask one short clarifying question in Russian to help distinguish between the options.",
            },
            {"role": "user", "content": f"Options:\n{lines}"},
        ],
    )
    return resp.choices[0].message.content.strip()
