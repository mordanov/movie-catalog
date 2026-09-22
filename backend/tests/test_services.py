import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---- TMDB ----


@pytest.mark.asyncio
async def test_tmdb_search_multi_returns_candidates():
    fake_results = [
        {
            "id": 862,
            "media_type": "movie",
            "title": "Toy Story",
            "original_title": "Toy Story",
            "release_date": "1995-11-22",
            "overview": "A cowboy doll...",
            "poster_path": "/toy.jpg",
            "genre_ids": [16, 35],
            "vote_average": 8.0,
        }
    ]
    fake_response = MagicMock()
    fake_response.json.return_value = {"results": fake_results}
    fake_response.raise_for_status = MagicMock()

    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fake_response
    ):
        from app.services.tmdb import search_multi

        results = await search_multi("Toy Story", language="en-US")

    assert len(results) == 1
    assert results[0]["tmdb_id"] == 862
    assert results[0]["title"] == "Toy Story"


@pytest.mark.asyncio
async def test_tmdb_get_details_movie():
    fake_detail = {
        "id": 862,
        "title": "Toy Story",
        "original_title": "Toy Story",
        "release_date": "1995-11-22",
        "overview": "A cowboy doll...",
        "poster_path": "/toy.jpg",
        "vote_average": 8.0,
        "genres": [{"id": 16, "name": "Animation"}],
        "credits": {"cast": [{"name": "Tom Hanks", "order": 0}]},
        "origin_country": ["US"],
    }
    fake_response = MagicMock()
    fake_response.json.return_value = fake_detail
    fake_response.raise_for_status = MagicMock()

    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fake_response
    ):
        from app.services.tmdb import get_details

        detail = await get_details(862, "movie", language="en-US")

    assert detail["title"] == "Toy Story"
    assert "Tom Hanks" in detail["actors"]


@pytest.mark.asyncio
async def test_tmdb_get_details_returns_trailer_url():
    fake_detail = {
        "id": 862,
        "title": "Toy Story",
        "release_date": "1995-11-22",
        "overview": "A cowboy doll...",
        "poster_path": "/toy.jpg",
        "vote_average": 8.0,
        "genres": [{"id": 16, "name": "Animation"}],
        "credits": {"cast": [{"name": f"Actor {i}", "order": i} for i in range(10)]},
        "videos": {
            "results": [
                {"type": "Teaser", "site": "YouTube", "key": "WRONG"},
                {"type": "Trailer", "site": "YouTube", "key": "abc123"},
                {"type": "Trailer", "site": "Vimeo", "key": "WRONG_VIMEO"},
            ]
        },
        "origin_country": ["US"],
    }
    fake_response = MagicMock()
    fake_response.json.return_value = fake_detail
    fake_response.raise_for_status = MagicMock()

    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fake_response
    ):
        from app.services.tmdb import get_details

        detail = await get_details(862, "movie", language="en-US")

    assert detail["trailer_url"] == "https://www.youtube.com/watch?v=abc123"
    assert len(detail["actors"]) == 5  # capped at 5


@pytest.mark.asyncio
async def test_tmdb_get_details_no_trailer_returns_none():
    fake_detail = {
        "id": 862,
        "title": "Toy Story",
        "release_date": "1995-11-22",
        "overview": "A cowboy doll...",
        "poster_path": "/toy.jpg",
        "vote_average": 8.0,
        "genres": [],
        "credits": {"cast": []},
        "videos": {"results": []},
        "origin_country": ["US"],
    }
    fake_response = MagicMock()
    fake_response.json.return_value = fake_detail
    fake_response.raise_for_status = MagicMock()

    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fake_response
    ):
        from app.services.tmdb import get_details

        detail = await get_details(862, "movie")

    assert detail["trailer_url"] is None


# ---- OpenAI ----


@pytest.mark.asyncio
async def test_openai_classify_returns_category():
    fake_choice = MagicMock()
    fake_choice.message.content = json.dumps(
        {"category": "cartoon", "cartoon_subtype": "pixar"}
    )
    fake_completion = MagicMock()
    fake_completion.choices = [fake_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_completion)

    with patch("app.services.openai_client._client", mock_client):
        from app.services.openai_client import classify_media

        result = await classify_media("Toy Story", ["Animation"], "A cowboy...", ["US"])

    assert result["category"] == "cartoon"
    assert result["cartoon_subtype"] == "pixar"


@pytest.mark.asyncio
async def test_openai_translate():
    fake_choice = MagicMock()
    fake_choice.message.content = "История игрушек"
    fake_completion = MagicMock()
    fake_completion.choices = [fake_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_completion)

    with patch("app.services.openai_client._client", mock_client):
        from app.services.openai_client import translate_to_russian

        result = await translate_to_russian("Toy Story")

    assert result == "История игрушек"
