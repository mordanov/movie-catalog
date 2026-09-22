from typing import Any

import httpx

from app.config import get_settings

_TMDB_BASE = "https://api.themoviedb.org/3"
_TMDB_IMG = "https://image.tmdb.org/t/p/w500"


def _poster(path: str | None) -> str | None:
    return f"{_TMDB_IMG}{path}" if path else None


async def search_multi(query: str, language: str = "ru-RU") -> list[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_TMDB_BASE}/search/multi",
            params={
                "api_key": get_settings().tmdb_api_key,
                "query": query,
                "language": language,
            },
        )
        resp.raise_for_status()
    results = []
    for r in resp.json().get("results", []):
        media_type = r.get("media_type")
        if media_type not in ("movie", "tv"):
            continue
        title = r.get("title") or r.get("name", "")
        release = r.get("release_date") or r.get("first_air_date", "")
        year = int(release[:4]) if release else None
        results.append(
            {
                "tmdb_id": r["id"],
                "media_type": media_type,
                "title": title,
                "year": year,
                "description": r.get("overview"),
                "poster_url": _poster(r.get("poster_path")),
                "genres": [],  # genre_ids (ints) at search level; names resolved in get_details
                "rating": r.get("vote_average"),
            }
        )
    return results


async def get_details(
    tmdb_id: int, media_type: str, language: str = "ru-RU"
) -> dict[str, Any]:
    """media_type: 'movie' or 'tv'"""
    endpoint = "movie" if media_type == "movie" else "tv"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_TMDB_BASE}/{endpoint}/{tmdb_id}",
            params={
                "api_key": get_settings().tmdb_api_key,
                "language": language,
                "append_to_response": "credits,videos",
            },
        )
        resp.raise_for_status()
    d = resp.json()
    title = d.get("title") or d.get("name", "")
    release = d.get("release_date") or d.get("first_air_date", "")
    year = int(release[:4]) if release else None
    genres = [g["name"] for g in d.get("genres", [])]
    actors = [c["name"] for c in d.get("credits", {}).get("cast", [])[:5]]
    origin = d.get(
        "origin_country", [d.get("production_countries", [{}])[0].get("iso_3166_1", "")]
    )
    trailer_url: str | None = None
    for v in d.get("videos", {}).get("results", []):
        if v.get("type") == "Trailer" and v.get("site") == "YouTube":
            trailer_url = f"https://www.youtube.com/watch?v={v['key']}"
            break
    return {
        "tmdb_id": tmdb_id,
        "media_type": media_type,
        "title": title,
        "year": year,
        "description": d.get("overview"),
        "poster_url": _poster(d.get("poster_path")),
        "genres": genres,
        "actors": actors,
        "rating": d.get("vote_average"),
        "origin_country": origin,
        "external_ids": {"tmdb": tmdb_id},
        "trailer_url": trailer_url,
    }
