import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
import pytest
from app.main import app
from app.auth import get_current_user


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: "testuser"
    yield
    app.dependency_overrides.pop(get_current_user, None)

FAKE_CANDIDATES = [
    {
        "tmdb_id": 862,
        "media_type": "movie",
        "title": "Toy Story",
        "year": 1995,
        "description": "A cowboy doll...",
        "poster_url": "https://image.tmdb.org/t/p/w500/toy.jpg",
        "genres": ["Animation"],
        "rating": 8.0,
    }
]

FAKE_DETAILS = {
    "tmdb_id": 862,
    "media_type": "movie",
    "title": "Toy Story",
    "year": 1995,
    "description": "История игрушек...",
    "poster_url": "https://image.tmdb.org/t/p/w500/toy.jpg",
    "genres": ["Animation"],
    "actors": ["Tom Hanks"],
    "rating": 8.0,
    "origin_country": ["US"],
    "external_ids": {"tmdb": 862},
}


@pytest.mark.asyncio
async def test_resolve_returns_candidates():
    with (
        patch(
            "app.routers.resolve_router.search_multi",
            new_callable=AsyncMock,
            return_value=FAKE_CANDIDATES,
        ),
        patch(
            "app.routers.resolve_router.classify_media",
            new_callable=AsyncMock,
            return_value={"category": "cartoon", "cartoon_subtype": "pixar"},
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/resolve", json={"query": "Toy Story"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tmdb_id"] == 862


@pytest.mark.asyncio
async def test_confirm_saves_to_db():
    with (
        patch(
            "app.routers.resolve_router.get_details",
            new_callable=AsyncMock,
            return_value=FAKE_DETAILS,
        ),
        patch(
            "app.routers.resolve_router.upload_poster",
            new_callable=AsyncMock,
            return_value="http://minio:9000/posters/862.jpg",
        ),
        patch(
            "app.routers.resolve_router.translate_to_russian",
            new_callable=AsyncMock,
            return_value="История игрушек",
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/media/confirm",
                json={
                    "tmdb_id": 862,
                    "media_type": "movie",
                    "category": "cartoon",
                    "cartoon_subtype": "pixar",
                    "source": "web_ui",
                },
            )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Toy Story"
