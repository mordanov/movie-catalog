import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import get_settings

# Pre-hash of "testpassword" — generated with:
# python3 -c "from passlib.context import CryptContext; ctx = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(ctx.hash('testpassword'))"
TEST_HASH = "$2b$12$PBIujP7l.KkKCA138yDNHuFoRiQQD4yBr94RoOljchuqGwoN7DSyG"


@pytest.fixture
def env_overrides(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("WEB_USER_1_LOGIN", "testuser")
    monkeypatch.setenv("WEB_USER_1_PASSWORD_HASH", TEST_HASH)
    monkeypatch.setenv("WEB_USER_2_LOGIN", "")
    monkeypatch.setenv("WEB_USER_2_PASSWORD_HASH", "")
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    monkeypatch.setenv("JWT_EXPIRE_HOURS", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("MINIO_ROOT_USER", "minio")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minio123")
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_success(env_overrides):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"login": "testuser", "password": "testpassword"})
    assert resp.status_code == 200
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(env_overrides):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"login": "testuser", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(env_overrides):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
