import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DB = "postgresql+asyncpg://catalog:changeme@localhost:5434/moviecatalog_test"


@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        # Set a fake auth cookie bypassing password check for these tests
        c.cookies.set("access_token", _make_test_token())
        yield c
    app.dependency_overrides.pop(get_db, None)


def _make_test_token():
    import os

    from app.auth import create_access_token

    os.environ.setdefault("JWT_SECRET", "testsecret")
    return create_access_token("testuser")


MEDIA_PAYLOAD = {
    "title": "Toy Story",
    "title_ru": "История игрушек",
    "year": 1995,
    "type": "cartoon",
    "category": "cartoon",
    "cartoon_subtype": "pixar",
    "genres": ["Animation", "Adventure"],
    "actors": [],
    "external_ids": {"tmdb": 862},
    "source": "web_ui",
    "watched_status": "not_watched",
}


@pytest.mark.asyncio
async def test_create_and_list(client):
    resp = await client.post("/api/media", json=MEDIA_PAYLOAD)
    assert resp.status_code == 201
    media_id = resp.json()["id"]

    resp = await client.get("/api/media")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(m["id"] == media_id for m in data["items"])


@pytest.mark.asyncio
async def test_get_by_id(client):
    resp = await client.post("/api/media", json=MEDIA_PAYLOAD)
    media_id = resp.json()["id"]
    resp = await client.get(f"/api/media/{media_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Toy Story"


@pytest.mark.asyncio
async def test_patch(client):
    resp = await client.post("/api/media", json=MEDIA_PAYLOAD)
    media_id = resp.json()["id"]
    resp = await client.patch(
        f"/api/media/{media_id}", json={"watched_status": "watched"}
    )
    assert resp.status_code == 200
    assert resp.json()["watched_status"] == "watched"


@pytest.mark.asyncio
async def test_delete(client):
    resp = await client.post("/api/media", json=MEDIA_PAYLOAD)
    media_id = resp.json()["id"]
    resp = await client.delete(f"/api/media/{media_id}")
    assert resp.status_code == 204
    resp = await client.get(f"/api/media/{media_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stats(client):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_category" in data
    assert "by_watched_status" in data


@pytest.mark.asyncio
async def test_random(client):
    await client.post("/api/media", json=MEDIA_PAYLOAD)
    resp = await client.get("/api/media/random")
    assert resp.status_code == 200
    assert "id" in resp.json()


@pytest.mark.asyncio
async def test_list_media_sort_by_rating(client, db_session):
    import uuid

    from app.models import Media, MediaCategory, MediaSource, MediaType, WatchedStatus

    for rating in [7.0, 9.0, 5.0]:
        db_session.add(
            Media(
                id=uuid.uuid4(),
                title=f"Movie {rating}",
                type=MediaType.movie,
                category=MediaCategory.adult_movie,
                watched_status=WatchedStatus.not_watched,
                source=MediaSource.web_ui,
                rating_external=rating,
                genres=[],
                actors=[],
                external_ids={},
            )
        )
    await db_session.commit()

    resp = await client.get("/api/media?sort_by=rating")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ratings = [i["rating_external"] for i in items if i["rating_external"] is not None]
    assert ratings == sorted(ratings, reverse=True)


@pytest.mark.asyncio
async def test_list_media_genre_filter(client, db_session):
    import uuid

    from app.models import Media, MediaCategory, MediaSource, MediaType, WatchedStatus

    db_session.add(
        Media(
            id=uuid.uuid4(),
            title="Animation Movie",
            type=MediaType.movie,
            category=MediaCategory.adult_movie,
            watched_status=WatchedStatus.not_watched,
            source=MediaSource.web_ui,
            genres=["Animation", "Comedy"],
            actors=[],
            external_ids={},
        )
    )
    db_session.add(
        Media(
            id=uuid.uuid4(),
            title="Drama Movie",
            type=MediaType.movie,
            category=MediaCategory.adult_movie,
            watched_status=WatchedStatus.not_watched,
            source=MediaSource.web_ui,
            genres=["Drama"],
            actors=[],
            external_ids={},
        )
    )
    await db_session.commit()

    resp = await client.get("/api/media?genre=Animation")
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()["items"]]
    assert "Animation Movie" in titles
    assert "Drama Movie" not in titles


@pytest.mark.asyncio
async def test_genres_endpoint(client, db_session):
    import uuid

    from app.models import Media, MediaCategory, MediaSource, MediaType, WatchedStatus

    db_session.add(
        Media(
            id=uuid.uuid4(),
            title="G1",
            type=MediaType.movie,
            category=MediaCategory.adult_movie,
            watched_status=WatchedStatus.not_watched,
            source=MediaSource.web_ui,
            genres=["Sci-Fi", "Action"],
            actors=[],
            external_ids={},
        )
    )
    await db_session.commit()

    resp = await client.get("/api/genres")
    assert resp.status_code == 200
    genres = resp.json()["genres"]
    assert "Sci-Fi" in genres
    assert "Action" in genres
