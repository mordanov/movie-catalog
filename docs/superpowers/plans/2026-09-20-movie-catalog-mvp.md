# Movie Catalog MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a movie/series/cartoon catalog with Telegram bot management and React web UI, deployable on a single VPS via Docker Compose.

**Architecture:** Monorepo with /backend (FastAPI), /bot (aiogram), /web (React+Vite), all sharing one PostgreSQL database through the backend API only. Bot and web communicate exclusively via HTTP to the backend — no direct DB access from bot or web. MinIO stores poster images; Caddy handles TLS and reverse proxying.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL 16, aiogram 3.x, React 18, Vite, TypeScript, Tailwind CSS v3, MinIO, Caddy 2, Docker Compose v2

**Spec:** docs/movie-catalog-spec.md

## Global Constraints

- Python 3.12+ (exact version in Dockerfiles)
- PostgreSQL 16
- aiogram 3.x (not 2.x — completely different API)
- All prompts to OpenAI must request JSON responses (except translation, which is plain text)
- poster_url in DB stores the internal MinIO URL, not the TMDB URL
- Bot users (bot_users table) and web users (.env variables) are completely independent auth systems
- INITIAL_ADMIN_TELEGRAM_ID: if bot_users table is empty at bot startup, auto-insert this ID
- Whitelist middleware caches DB lookups for 30–60 seconds (in-memory dict with expiry)
- Web passwords stored as bcrypt hashes only — never plaintext in .env
- JWT delivered as httpOnly cookie for web auth
- TMDB API base URL: https://api.themoviedb.org/3
- TMDB image base: https://image.tmdb.org/t/p/w500

---

## Task 1: Project Scaffolding

**Files:**
- Create: `docker-compose.yml`
- Create: `Caddyfile`
- Create: `.env.example`
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `bot/Dockerfile`
- Create: `bot/requirements.txt`
- Create: `web/Dockerfile`
- Create: `web/nginx.conf`

**Interfaces:**
- Consumes: nothing (green-field)
- Produces: runnable docker-compose stack skeleton; all subsequent tasks build inside this structure

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/app/routers backend/app/services backend/alembic/versions
mkdir -p bot/handlers bot/middlewares bot/tests
mkdir -p web/src/components web/src/pages
mkdir -p docs/superpowers/plans
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: moviecatalog
      POSTGRES_USER: ${POSTGRES_USER:-catalog}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-catalog}"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:?required}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?required}
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-catalog}:${POSTGRES_PASSWORD}@postgres:5432/moviecatalog
      OPENAI_API_KEY: ${OPENAI_API_KEY:?required}
      TMDB_API_KEY: ${TMDB_API_KEY:?required}
      MINIO_ENDPOINT: minio:9000
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      MINIO_BUCKET: ${MINIO_BUCKET:-posters}
      WEB_USER_1_LOGIN: ${WEB_USER_1_LOGIN:?required}
      WEB_USER_1_PASSWORD_HASH: ${WEB_USER_1_PASSWORD_HASH:?required}
      WEB_USER_2_LOGIN: ${WEB_USER_2_LOGIN:-}
      WEB_USER_2_PASSWORD_HASH: ${WEB_USER_2_PASSWORD_HASH:-}
      JWT_SECRET: ${JWT_SECRET:?required}
      JWT_EXPIRE_HOURS: ${JWT_EXPIRE_HOURS:-72}
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy

  bot:
    build: ./bot
    restart: unless-stopped
    environment:
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:?required}
      INITIAL_ADMIN_TELEGRAM_ID: ${INITIAL_ADMIN_TELEGRAM_ID:?required}
      BACKEND_URL: http://backend:8000
    depends_on:
      - backend

  web:
    build: ./web
    restart: unless-stopped
    depends_on:
      - backend

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - web
    environment:
      DOMAIN: ${DOMAIN:?required}

volumes:
  pg_data:
  minio_data:
  caddy_data:
  caddy_config:
```

- [ ] **Step 3: Write `Caddyfile`**

```caddyfile
{$DOMAIN} {
    # API proxied to backend
    handle /api/* {
        reverse_proxy backend:8000
    }

    # Everything else served by the React SPA container
    handle {
        reverse_proxy web:80
    }

    encode gzip
    log {
        output stdout
    }
}
```

- [ ] **Step 4: Write `.env.example`**

```dotenv
# Postgres
POSTGRES_USER=catalog
POSTGRES_PASSWORD=changeme

# Backend
DATABASE_URL=postgresql+asyncpg://catalog:changeme@postgres:5432/moviecatalog
OPENAI_API_KEY=sk-...
TMDB_API_KEY=...
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=posters

# Web auth — generate hash: python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpassword'))"
WEB_USER_1_LOGIN=admin
WEB_USER_1_PASSWORD_HASH=$2b$12$...
WEB_USER_2_LOGIN=
WEB_USER_2_PASSWORD_HASH=

JWT_SECRET=change-me-to-a-long-random-string
JWT_EXPIRE_HOURS=72

# Bot
TELEGRAM_BOT_TOKEN=123456789:ABC...
INITIAL_ADMIN_TELEGRAM_ID=123456789

# Caddy
DOMAIN=catalog.example.com
```

- [ ] **Step 5: Write `backend/Dockerfile` and `backend/requirements.txt`**

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`backend/requirements.txt`:
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic-settings==2.2.1
httpx==0.27.0
python-multipart==0.0.9
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
minio==7.2.7
openai==1.30.0
```

- [ ] **Step 6: Write `bot/Dockerfile` and `bot/requirements.txt`**

`bot/Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

`bot/requirements.txt`:
```
aiogram==3.7.0
pydantic-settings==2.2.1
httpx==0.27.0
cachetools==5.3.3
```

- [ ] **Step 7: Write `web/Dockerfile` and `web/nginx.conf`**

`web/Dockerfile`:
```dockerfile
# Build stage
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

`web/nginx.conf`:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;
}
```

- [ ] **Step 8: Validate and commit**

```bash
docker-compose config   # must produce no errors
git add -A
git commit -m "Task 1: project scaffolding — docker-compose, Dockerfiles, .env.example"
```

---

## Task 2: Database Models + Alembic

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial_schema.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `DATABASE_URL` env var, Task 1 backend container
- Produces: `Media` and `BotUser` ORM classes, `get_db` async dependency, initial migration

- [ ] **Step 1: Write `backend/tests/test_models.py`** (run first — should fail until models exist)

```python
"""Tests that all enum values match the spec."""
from app.models import MediaType, MediaCategory, CartoonSubtype, WatchedStatus, MediaSource


def test_media_type_values():
    assert {e.value for e in MediaType} == {"movie", "cartoon", "series"}


def test_media_category_values():
    assert {e.value for e in MediaCategory} == {
        "kids_series", "adult_series", "family_movie", "adult_movie", "cartoon"
    }


def test_cartoon_subtype_values():
    assert {e.value for e in CartoonSubtype} == {
        "disney", "pixar", "soviet", "russian", "other"
    }


def test_watched_status_values():
    assert {e.value for e in WatchedStatus} == {
        "not_watched", "watching", "watched"
    }


def test_media_source_values():
    assert {e.value for e in MediaSource} == {
        "telegram_text", "telegram_screenshot", "web_ui"
    }
```

- [ ] **Step 2: Write `backend/app/models.py`**

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, DateTime, Enum, Float, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MediaType(str, enum.Enum):
    movie = "movie"
    cartoon = "cartoon"
    series = "series"


class MediaCategory(str, enum.Enum):
    kids_series = "kids_series"
    adult_series = "adult_series"
    family_movie = "family_movie"
    adult_movie = "adult_movie"
    cartoon = "cartoon"


class CartoonSubtype(str, enum.Enum):
    disney = "disney"
    pixar = "pixar"
    soviet = "soviet"
    russian = "russian"
    other = "other"


class WatchedStatus(str, enum.Enum):
    not_watched = "not_watched"
    watching = "watching"
    watched = "watched"


class MediaSource(str, enum.Enum):
    telegram_text = "telegram_text"
    telegram_screenshot = "telegram_screenshot"
    web_ui = "web_ui"


class Media(Base):
    __tablename__ = "media"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_ru: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    type: Mapped[MediaType] = mapped_column(Enum(MediaType, name="media_type"), nullable=False)
    category: Mapped[MediaCategory] = mapped_column(Enum(MediaCategory, name="media_category"), nullable=False)
    cartoon_subtype: Mapped[CartoonSubtype | None] = mapped_column(
        Enum(CartoonSubtype, name="cartoon_subtype"), nullable=True
    )
    genres: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    actors: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    external_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    rating_external: Mapped[float | None] = mapped_column(Float, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    watched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    watched_status: Mapped[WatchedStatus] = mapped_column(
        Enum(WatchedStatus, name="watched_status"),
        nullable=False,
        default=WatchedStatus.not_watched,
        server_default="not_watched",
    )
    source: Mapped[MediaSource] = mapped_column(Enum(MediaSource, name="media_source"), nullable=False)
    added_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BotUser(Base):
    __tablename__ = "bot_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 3: Write `backend/app/database.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: Configure Alembic for async**

Run `alembic init alembic` inside `backend/`, then replace `backend/alembic/env.py`:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

In `backend/alembic.ini` set:
```
sqlalchemy.url = %(DATABASE_URL)s
```

- [ ] **Step 5: Write `backend/alembic/versions/001_initial_schema.py`**

```python
"""initial schema

Revision ID: 001initial
Revises:
Create Date: 2026-09-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE media_type AS ENUM ('movie', 'cartoon', 'series')")
    op.execute("CREATE TYPE media_category AS ENUM ('kids_series', 'adult_series', 'family_movie', 'adult_movie', 'cartoon')")
    op.execute("CREATE TYPE cartoon_subtype AS ENUM ('disney', 'pixar', 'soviet', 'russian', 'other')")
    op.execute("CREATE TYPE watched_status AS ENUM ('not_watched', 'watching', 'watched')")
    op.execute("CREATE TYPE media_source AS ENUM ('telegram_text', 'telegram_screenshot', 'web_ui')")

    op.create_table(
        "media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("title_ru", sa.String(500), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("poster_url", sa.String(2048), nullable=True),
        sa.Column("type", postgresql.ENUM(name="media_type", create_type=False), nullable=False),
        sa.Column("category", postgresql.ENUM(name="media_category", create_type=False), nullable=False),
        sa.Column("cartoon_subtype", postgresql.ENUM(name="cartoon_subtype", create_type=False), nullable=True),
        sa.Column("genres", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("actors", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("external_ids", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("rating_external", sa.Float, nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("watched_status", postgresql.ENUM(name="watched_status", create_type=False), nullable=False, server_default="not_watched"),
        sa.Column("source", postgresql.ENUM(name="media_source", create_type=False), nullable=False),
        sa.Column("added_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_table(
        "bot_users",
        sa.Column("telegram_id", sa.BigInteger, primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("added_by_telegram_id", sa.BigInteger, nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("media")
    op.drop_table("bot_users")
    for t in ("media_type", "media_category", "cartoon_subtype", "watched_status", "media_source"):
        op.execute(f"DROP TYPE {t}")
```

- [ ] **Step 6: Apply migration and run tests**

```bash
cd backend
alembic upgrade head
python -m pytest tests/test_models.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "Task 2: database models, alembic migration, enum tests"
```

---

## Task 3: Backend Core — Config, Auth, App Entry

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/auth.py`
- Create: `backend/app/routers/auth_router.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `WEB_USER_1_LOGIN`, `WEB_USER_1_PASSWORD_HASH`, `WEB_USER_2_*`, `JWT_SECRET`, `JWT_EXPIRE_HOURS`
- Produces: POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me; `get_current_user` FastAPI dependency

- [ ] **Step 1: Write failing `backend/tests/test_auth.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

# Pre-hash of "testpassword" — generate with: python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('testpassword'))"
TEST_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

@pytest.fixture
def env_overrides(monkeypatch):
    monkeypatch.setenv("WEB_USER_1_LOGIN", "testuser")
    monkeypatch.setenv("WEB_USER_1_PASSWORD_HASH", TEST_HASH)
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    monkeypatch.setenv("JWT_EXPIRE_HOURS", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("MINIO_ROOT_USER", "minio")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minio123")


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
```

- [ ] **Step 2: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    openai_api_key: str = ""
    tmdb_api_key: str = ""

    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "posters"

    web_user_1_login: str = ""
    web_user_1_password_hash: str = ""
    web_user_2_login: str = ""
    web_user_2_password_hash: str = ""

    jwt_secret: str = "change-me"
    jwt_expire_hours: int = 72


settings = Settings()
```

- [ ] **Step 3: Write `backend/app/auth.py`**

```python
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def _users() -> dict[str, str]:
    """Return {login: hash} for all configured web users."""
    users: dict[str, str] = {}
    if settings.web_user_1_login and settings.web_user_1_password_hash:
        users[settings.web_user_1_login] = settings.web_user_1_password_hash
    if settings.web_user_2_login and settings.web_user_2_password_hash:
        users[settings.web_user_2_login] = settings.web_user_2_password_hash
    return users


def authenticate_user(login: str, password: str) -> str | None:
    """Return login if valid, else None."""
    users = _users()
    hashed = users.get(login)
    if hashed and verify_password(password, hashed):
        return login
    return None


def create_access_token(login: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode({"sub": login, "exp": expire}, settings.jwt_secret, algorithm="HS256")


def get_current_user(access_token: str | None = Cookie(default=None)) -> str:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, settings.jwt_secret, algorithms=["HS256"])
        login: str = payload.get("sub", "")
        if not login:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return login
```

- [ ] **Step 4: Write `backend/app/routers/auth_router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.auth import authenticate_user, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    login_str = authenticate_user(body.login, body.password)
    if not login_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(login_str)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 72,
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me")
async def me(current_user: str = Depends(get_current_user)):
    return {"login": current_user}
```

- [ ] **Step 5: Write `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth_router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: could run alembic upgrade head here via subprocess in dev
    yield


app = FastAPI(title="Movie Catalog API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Caddy handles real origin restriction
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
```

- [ ] **Step 6: Run auth tests and fix until passing**

```bash
cd backend
python -m pytest tests/test_auth.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/app/auth.py backend/app/routers/auth_router.py backend/app/main.py backend/tests/test_auth.py
git commit -m "Task 3: backend config, bcrypt/JWT auth, /api/auth routes"
```

---

## Task 4: Backend Media CRUD + Stats + Random

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/media_router.py`
- Test: `backend/tests/test_media.py`

**Interfaces:**
- Consumes: `Media` ORM model, `get_db` dependency, `get_current_user` dependency
- Produces: GET /api/media, POST /api/media, GET /api/media/{id}, PATCH /api/media/{id}, DELETE /api/media/{id}, GET /api/media/random, GET /api/stats

- [ ] **Step 1: Write failing `backend/tests/test_media.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.main import app
from app.database import get_db
from app.models import Base

TEST_DB = "postgresql+asyncpg://catalog:changeme@localhost/moviecatalog_test"

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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Set a fake auth cookie bypassing password check for these tests
        c.cookies.set("access_token", _make_test_token())
        yield c
    app.dependency_overrides.clear()

def _make_test_token():
    from app.auth import create_access_token
    import os
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
    resp = await client.patch(f"/api/media/{media_id}", json={"watched_status": "watched"})
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
```

- [ ] **Step 2: Write `backend/app/schemas.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import CartoonSubtype, MediaCategory, MediaSource, MediaType, WatchedStatus


class MediaCreate(BaseModel):
    title: str
    title_ru: str | None = None
    year: int | None = None
    description: str | None = None
    poster_url: str | None = None
    type: MediaType
    category: MediaCategory
    cartoon_subtype: CartoonSubtype | None = None
    genres: list[str] = []
    actors: list[str] = []
    external_ids: dict = {}
    rating_external: float | None = None
    watched_status: WatchedStatus = WatchedStatus.not_watched
    source: MediaSource
    added_by: str | None = None
    notes: str | None = None


class MediaUpdate(BaseModel):
    title: str | None = None
    title_ru: str | None = None
    year: int | None = None
    description: str | None = None
    poster_url: str | None = None
    type: MediaType | None = None
    category: MediaCategory | None = None
    cartoon_subtype: CartoonSubtype | None = None
    genres: list[str] | None = None
    actors: list[str] | None = None
    rating_external: float | None = None
    watched_status: WatchedStatus | None = None
    watched_at: datetime | None = None
    notes: str | None = None


class MediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    title_ru: str | None
    year: int | None
    description: str | None
    poster_url: str | None
    type: MediaType
    category: MediaCategory
    cartoon_subtype: CartoonSubtype | None
    genres: list[str]
    actors: list[str]
    external_ids: dict
    rating_external: float | None
    added_at: datetime
    watched_at: datetime | None
    watched_status: WatchedStatus
    source: MediaSource
    added_by: str | None
    notes: str | None


class MediaListResponse(BaseModel):
    items: list[MediaResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    by_category: dict[str, int]
    by_watched_status: dict[str, int]


class CandidateResponse(BaseModel):
    tmdb_id: int
    media_type: str  # "movie" or "tv"
    title: str
    title_ru: str | None
    year: int | None
    description: str | None
    poster_url: str | None
    genres: list[str]
    rating: float | None
    disambiguation_question: str | None = None
```

- [ ] **Step 3: Write `backend/app/routers/media_router.py`**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Media, MediaCategory, MediaType, WatchedStatus
from app.schemas import MediaCreate, MediaListResponse, MediaResponse, MediaUpdate, StatsResponse

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: MediaCategory | None = None,
    type: MediaType | None = None,
    watched_status: WatchedStatus | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    q = select(Media)
    if category:
        q = q.where(Media.category == category)
    if type:
        q = q.where(Media.type == type)
    if watched_status:
        q = q.where(Media.watched_status == watched_status)
    if search:
        pattern = f"%{search}%"
        q = q.where(Media.title.ilike(pattern) | Media.title_ru.ilike(pattern))

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar_one()

    q = q.order_by(Media.added_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(q)).scalars().all()
    return MediaListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/random", response_model=MediaResponse)
async def random_media(
    category: MediaCategory | None = None,
    type: MediaType | None = None,
    watched_status: WatchedStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    q = select(Media)
    if category:
        q = q.where(Media.category == category)
    if type:
        q = q.where(Media.type == type)
    if watched_status:
        q = q.where(Media.watched_status == watched_status)
    q = q.order_by(func.random()).limit(1)
    result = (await db.execute(q)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="No media found")
    return result


@router.get("/stats", response_model=StatsResponse)
async def stats(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    total = (await db.execute(select(func.count(Media.id)))).scalar_one()

    by_type: dict[str, int] = {}
    for row in (await db.execute(select(Media.type, func.count()).group_by(Media.type))).all():
        by_type[row[0].value] = row[1]

    by_category: dict[str, int] = {}
    for row in (await db.execute(select(Media.category, func.count()).group_by(Media.category))).all():
        by_category[row[0].value] = row[1]

    by_watched: dict[str, int] = {}
    for row in (await db.execute(select(Media.watched_status, func.count()).group_by(Media.watched_status))).all():
        by_watched[row[0].value] = row[1]

    return StatsResponse(total=total, by_type=by_type, by_category=by_category, by_watched_status=by_watched)


@router.post("", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def create_media(
    body: MediaCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = Media(**body.model_dump())
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    return media


@router.patch("/{media_id}", response_model=MediaResponse)
async def patch_media(
    media_id: uuid.UUID,
    body: MediaUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(media, field, value)
    await db.commit()
    await db.refresh(media)
    return media


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(media)
    await db.commit()
```

Add `media_router` to `backend/app/main.py`:

```python
from app.routers.media_router import router as media_router
# ... inside create_app or after app definition:
app.include_router(media_router)
```

- [ ] **Step 4: Run tests and fix until passing**

```bash
cd backend
python -m pytest tests/test_media.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/media_router.py backend/app/main.py backend/tests/test_media.py
git commit -m "Task 4: media CRUD, /api/stats, /api/media/random"
```

---

## Task 5: External Services — TMDB, OpenAI, MinIO

**Files:**
- Create: `backend/app/services/tmdb.py`
- Create: `backend/app/services/openai_client.py`
- Create: `backend/app/services/storage.py`
- Test: `backend/tests/test_services.py`

**Interfaces:**
- Consumes: `TMDB_API_KEY`, `OPENAI_API_KEY`, `MINIO_*` env vars
- Produces: `search_multi`, `get_details`, `translate_to_russian`, `classify_media`, `extract_from_screenshot`, `generate_disambiguation_question`, `upload_poster`

- [ ] **Step 1: Write `backend/tests/test_services.py`** with mocked HTTP

```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---- TMDB ----

@pytest.mark.asyncio
async def test_tmdb_search_multi_returns_candidates():
    fake_results = [
        {"id": 862, "media_type": "movie", "title": "Toy Story",
         "original_title": "Toy Story", "release_date": "1995-11-22",
         "overview": "A cowboy doll...", "poster_path": "/toy.jpg",
         "genre_ids": [16, 35], "vote_average": 8.0}
    ]
    fake_response = MagicMock()
    fake_response.json.return_value = {"results": fake_results}
    fake_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fake_response):
        from app.services.tmdb import search_multi
        results = await search_multi("Toy Story", language="en-US")

    assert len(results) == 1
    assert results[0]["tmdb_id"] == 862
    assert results[0]["title"] == "Toy Story"


@pytest.mark.asyncio
async def test_tmdb_get_details_movie():
    fake_detail = {
        "id": 862, "title": "Toy Story", "original_title": "Toy Story",
        "release_date": "1995-11-22", "overview": "A cowboy doll...",
        "poster_path": "/toy.jpg", "vote_average": 8.0,
        "genres": [{"id": 16, "name": "Animation"}],
        "credits": {"cast": [{"name": "Tom Hanks", "order": 0}]},
        "origin_country": ["US"],
    }
    fake_response = MagicMock()
    fake_response.json.return_value = fake_detail
    fake_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fake_response):
        from app.services.tmdb import get_details
        detail = await get_details(862, "movie", language="en-US")

    assert detail["title"] == "Toy Story"
    assert "Tom Hanks" in detail["actors"]


# ---- OpenAI ----

@pytest.mark.asyncio
async def test_openai_classify_returns_category():
    fake_choice = MagicMock()
    fake_choice.message.content = json.dumps({"category": "cartoon", "cartoon_subtype": "pixar"})
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
```

- [ ] **Step 2: Write `backend/app/services/tmdb.py`**

```python
from typing import Any

import httpx

from app.config import settings

_TMDB_BASE = "https://api.themoviedb.org/3"
_TMDB_IMG = "https://image.tmdb.org/t/p/w500"


def _poster(path: str | None) -> str | None:
    return f"{_TMDB_IMG}{path}" if path else None


async def search_multi(query: str, language: str = "ru-RU") -> list[dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_TMDB_BASE}/search/multi",
            params={"api_key": settings.tmdb_api_key, "query": query, "language": language},
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
        results.append({
            "tmdb_id": r["id"],
            "media_type": media_type,
            "title": title,
            "year": year,
            "description": r.get("overview"),
            "poster_url": _poster(r.get("poster_path")),
            "genres": r.get("genre_ids", []),  # IDs only at search level
            "rating": r.get("vote_average"),
        })
    return results


async def get_details(tmdb_id: int, media_type: str, language: str = "ru-RU") -> dict[str, Any]:
    """media_type: 'movie' or 'tv'"""
    endpoint = "movie" if media_type == "movie" else "tv"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_TMDB_BASE}/{endpoint}/{tmdb_id}",
            params={"api_key": settings.tmdb_api_key, "language": language, "append_to_response": "credits"},
        )
        resp.raise_for_status()
    d = resp.json()
    title = d.get("title") or d.get("name", "")
    release = d.get("release_date") or d.get("first_air_date", "")
    year = int(release[:4]) if release else None
    genres = [g["name"] for g in d.get("genres", [])]
    actors = [c["name"] for c in d.get("credits", {}).get("cast", [])[:10]]
    origin = d.get("origin_country", [d.get("production_countries", [{}])[0].get("iso_3166_1", "")])
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
    }
```

- [ ] **Step 3: Write `backend/app/services/openai_client.py`**

```python
import json
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_CLASSIFY_SYSTEM = """You classify movies/cartoons/series into catalog categories.
Given title, genres, description, and origin country, return JSON only:
{"category": "<kids_series|adult_series|family_movie|adult_movie|cartoon>",
 "cartoon_subtype": "<disney|pixar|soviet|russian|other|null>"}
cartoon_subtype is null if category is not cartoon."""

_EXTRACT_SYSTEM = """You extract movie/series info from a screenshot description.
Return JSON only: {"title": "<best guess title>", "year_hint": <int or null>}"""


async def translate_to_russian(text: str) -> str:
    """Translate text to Russian. Returns plain string."""
    resp = await _client.chat.completions.create(
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
    resp = await _client.chat.completions.create(
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
    resp = await _client.chat.completions.create(
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
    resp = await _client.chat.completions.create(
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
```

- [ ] **Step 4: Write `backend/app/services/storage.py`**

```python
import io
from urllib.parse import urlparse

import httpx
from minio import Minio
from minio.error import S3Error

from app.config import settings

_client: Minio | None = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=False,
        )
        try:
            if not _client.bucket_exists(settings.minio_bucket):
                _client.make_bucket(settings.minio_bucket)
        except S3Error:
            pass
    return _client


async def upload_poster(url: str, filename: str) -> str:
    """Download poster from URL and upload to MinIO. Returns internal URL."""
    async with httpx.AsyncClient() as http:
        resp = await http.get(url, follow_redirects=True)
        resp.raise_for_status()

    client = _get_client()
    data = resp.content
    client.put_object(
        settings.minio_bucket,
        filename,
        io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg",
    )
    return f"http://{settings.minio_endpoint}/{settings.minio_bucket}/{filename}"
```

- [ ] **Step 5: Run service tests**

```bash
cd backend
python -m pytest tests/test_services.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ backend/tests/test_services.py
git commit -m "Task 5: TMDB, OpenAI, MinIO service clients with mocked tests"
```

---

## Task 6: Resolve Endpoints + Confirm

**Files:**
- Create: `backend/app/routers/resolve_router.py`
- Test: `backend/tests/test_resolve.py`

**Interfaces:**
- Consumes: `tmdb`, `openai_client`, `storage` services; `Media` model; `get_db` dependency
- Produces: POST /api/resolve, POST /api/resolve/screenshot, POST /api/media/confirm

- [ ] **Step 1: Write failing `backend/tests/test_resolve.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth import get_current_user

app.dependency_overrides[get_current_user] = lambda: "testuser"

FAKE_CANDIDATES = [
    {
        "tmdb_id": 862, "media_type": "movie", "title": "Toy Story",
        "year": 1995, "description": "A cowboy doll...",
        "poster_url": "https://image.tmdb.org/t/p/w500/toy.jpg",
        "genres": ["Animation"], "rating": 8.0,
    }
]

FAKE_DETAILS = {
    "tmdb_id": 862, "media_type": "movie", "title": "Toy Story",
    "year": 1995, "description": "История игрушек...",
    "poster_url": "https://image.tmdb.org/t/p/w500/toy.jpg",
    "genres": ["Animation"], "actors": ["Tom Hanks"],
    "rating": 8.0, "origin_country": ["US"],
    "external_ids": {"tmdb": 862},
}


@pytest.mark.asyncio
async def test_resolve_returns_candidates():
    with patch("app.routers.resolve_router.search_multi", new_callable=AsyncMock, return_value=FAKE_CANDIDATES), \
         patch("app.routers.resolve_router.classify_media", new_callable=AsyncMock, return_value={"category": "cartoon", "cartoon_subtype": "pixar"}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/resolve", json={"query": "Toy Story"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tmdb_id"] == 862


@pytest.mark.asyncio
async def test_confirm_saves_to_db():
    with patch("app.routers.resolve_router.get_details", new_callable=AsyncMock, return_value=FAKE_DETAILS), \
         patch("app.routers.resolve_router.upload_poster", new_callable=AsyncMock, return_value="http://minio:9000/posters/862.jpg"), \
         patch("app.routers.resolve_router.translate_to_russian", new_callable=AsyncMock, return_value="История игрушек"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/media/confirm", json={
                "tmdb_id": 862, "media_type": "movie",
                "category": "cartoon", "cartoon_subtype": "pixar",
                "source": "web_ui",
            })
    assert resp.status_code == 201
    assert resp.json()["title"] == "Toy Story"
```

- [ ] **Step 2: Write `backend/app/routers/resolve_router.py`**

```python
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import CartoonSubtype, Media, MediaCategory, MediaSource, MediaType, WatchedStatus
from app.schemas import CandidateResponse, MediaResponse
from app.services.openai_client import (
    classify_media,
    extract_from_screenshot,
    generate_disambiguation_question,
    translate_to_russian,
)
from app.services.storage import upload_poster
from app.services.tmdb import get_details, search_multi

router = APIRouter(tags=["resolve"])


class ResolveRequest(BaseModel):
    query: str


class ConfirmRequest(BaseModel):
    tmdb_id: int
    media_type: str  # "movie" or "tv"
    category: MediaCategory
    cartoon_subtype: CartoonSubtype | None = None
    source: MediaSource
    added_by: str | None = None
    notes: str | None = None


@router.post("/api/resolve", response_model=list[CandidateResponse])
async def resolve(
    body: ResolveRequest,
    _user: str = Depends(get_current_user),
):
    # Try Russian first, fall back to English
    candidates = await search_multi(body.query, language="ru-RU")
    if not candidates:
        candidates = await search_multi(body.query, language="en-US")

    if not candidates:
        return []

    disambiguation_question = None
    if len(candidates) == 1:
        # Pre-classify the single result
        c = candidates[0]
        classification = await classify_media(
            c["title"], c.get("genres", []), c.get("description"), []
        )
        c["category"] = classification.get("category")
        c["cartoon_subtype"] = classification.get("cartoon_subtype")
    else:
        disambiguation_question = await generate_disambiguation_question(candidates[:5])

    result = []
    for c in candidates[:5]:
        result.append(CandidateResponse(
            tmdb_id=c["tmdb_id"],
            media_type=c["media_type"],
            title=c["title"],
            title_ru=None,
            year=c.get("year"),
            description=c.get("description"),
            poster_url=c.get("poster_url"),
            genres=c.get("genres", []),
            rating=c.get("rating"),
            disambiguation_question=disambiguation_question if len(candidates) > 1 else None,
        ))
    return result


@router.post("/api/resolve/screenshot", response_model=list[CandidateResponse])
async def resolve_screenshot(
    file: UploadFile = File(...),
    _user: str = Depends(get_current_user),
):
    image_bytes = await file.read()
    extracted = await extract_from_screenshot(image_bytes)
    title = extracted.get("title", "")
    if not title:
        raise HTTPException(status_code=422, detail="Could not extract title from screenshot")

    candidates = await search_multi(title, language="ru-RU")
    if not candidates:
        candidates = await search_multi(title, language="en-US")

    disambiguation_question = None
    if len(candidates) > 1:
        disambiguation_question = await generate_disambiguation_question(candidates[:5])

    return [
        CandidateResponse(
            tmdb_id=c["tmdb_id"],
            media_type=c["media_type"],
            title=c["title"],
            title_ru=None,
            year=c.get("year"),
            description=c.get("description"),
            poster_url=c.get("poster_url"),
            genres=c.get("genres", []),
            rating=c.get("rating"),
            disambiguation_question=disambiguation_question,
        )
        for c in candidates[:5]
    ]


@router.post("/api/media/confirm", response_model=MediaResponse, status_code=201)
async def confirm(
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    # Fetch full details from TMDB
    details = await get_details(body.tmdb_id, body.media_type, language="ru-RU")

    # Fall back to English and translate description if no Russian overview
    if not details.get("description"):
        details_en = await get_details(body.tmdb_id, body.media_type, language="en-US")
        if details_en.get("description"):
            details["description"] = await translate_to_russian(details_en["description"])
        details["title"] = details.get("title") or details_en.get("title", "")

    # Determine media type from TMDB media_type field
    orm_type = MediaType.movie if body.media_type == "movie" else MediaType.series

    # Download poster to MinIO
    poster_url = None
    if details.get("poster_url"):
        filename = f"{body.tmdb_id}_{body.media_type}.jpg"
        poster_url = await upload_poster(details["poster_url"], filename)

    media = Media(
        id=uuid.uuid4(),
        title=details["title"],
        year=details.get("year"),
        description=details.get("description"),
        poster_url=poster_url,
        type=orm_type,
        category=body.category,
        cartoon_subtype=body.cartoon_subtype,
        genres=details.get("genres", []),
        actors=details.get("actors", []),
        external_ids=details.get("external_ids", {"tmdb": body.tmdb_id}),
        rating_external=details.get("rating"),
        watched_status=WatchedStatus.not_watched,
        source=body.source,
        added_by=body.added_by,
        notes=body.notes,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media
```

Add `resolve_router` to `backend/app/main.py`:
```python
from app.routers.resolve_router import router as resolve_router
app.include_router(resolve_router)
```

- [ ] **Step 3: Run tests**

```bash
cd backend
python -m pytest tests/test_resolve.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/resolve_router.py backend/tests/test_resolve.py backend/app/main.py
git commit -m "Task 6: /api/resolve, /api/resolve/screenshot, /api/media/confirm"
```

---

## Task 7: Bot — Scaffolding, Auth Middleware, User Management, Misc Commands

**Files:**
- Create: `bot/config.py`
- Create: `bot/states.py`
- Create: `bot/middlewares/auth.py`
- Create: `bot/handlers/users.py`
- Create: `bot/handlers/misc.py`
- Create: `bot/main.py`
- Create: `backend/app/routers/bot_router.py`
- Test: `bot/tests/test_middleware.py`

**Interfaces:**
- Consumes: `TELEGRAM_BOT_TOKEN`, `INITIAL_ADMIN_TELEGRAM_ID`, `BACKEND_URL` env vars; backend /api/bot/users/* endpoints
- Produces: runnable aiogram bot with whitelist auth, /start, /help, /stats, /random, /adduser, /removeuser, /users

- [ ] **Step 1: Write `bot/tests/test_middleware.py`**

```python
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
```

- [ ] **Step 2: Write `bot/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str
    initial_admin_telegram_id: int
    backend_url: str = "http://backend:8000"


settings = Settings()
```

- [ ] **Step 3: Write `bot/states.py`**

```python
from aiogram.fsm.state import State, StatesGroup


class AddMedia(StatesGroup):
    waiting_title = State()
    showing_candidates = State()
    confirming_category = State()
    confirming_add = State()


class EditMedia(StatesGroup):
    choosing_field = State()
    entering_value = State()


class DeleteConfirm(StatesGroup):
    confirming = State()
```

- [ ] **Step 4: Write `backend/app/routers/bot_router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BotUser

router = APIRouter(prefix="/api/bot", tags=["bot"])


class AddUserRequest(BaseModel):
    telegram_id: int
    display_name: str | None = None
    added_by_telegram_id: int | None = None


@router.get("/users/{telegram_id}")
async def check_user(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(BotUser, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    return {"telegram_id": user.telegram_id, "display_name": user.display_name}


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(BotUser).order_by(BotUser.added_at))).scalars().all()
    return [{"telegram_id": u.telegram_id, "display_name": u.display_name, "added_at": u.added_at} for u in users]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def add_user(body: AddUserRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.get(BotUser, body.telegram_id)
    if existing:
        raise HTTPException(status_code=409, detail="Already exists")
    user = BotUser(
        telegram_id=body.telegram_id,
        display_name=body.display_name,
        added_by_telegram_id=body.added_by_telegram_id,
    )
    db.add(user)
    await db.commit()
    return {"telegram_id": user.telegram_id}


@router.delete("/users/{telegram_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(BotUser, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(user)
    await db.commit()
```

Add to `backend/app/main.py`:
```python
from app.routers.bot_router import router as bot_router
app.include_router(bot_router)
```

- [ ] **Step 5: Write `bot/middlewares/auth.py`**

```python
from typing import Any, Callable, Awaitable

import httpx
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from cachetools import TTLCache


class WhitelistMiddleware(BaseMiddleware):
    # ponytail: in-memory TTLCache, single instance per process; fine for one-bot one-process deployment
    def __init__(self, backend_url: str, ttl: int = 60):
        self._backend_url = backend_url
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
                    resp = await client.get(f"{self._backend_url}/api/bot/users/{tid}", timeout=5)
                allowed = resp.status_code == 200
            except Exception:
                allowed = False
            self._cache[tid] = allowed

        if not allowed:
            if isinstance(event, Message):
                await event.answer("У вас нет доступа к этому боту.")
            return

        return await handler(event, data)
```

- [ ] **Step 6: Write `bot/handlers/users.py`**

```python
import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url


@router.message(Command("adduser"))
async def cmd_adduser(message: Message):
    """Usage: /adduser <telegram_id> [display_name]"""
    args = (message.text or "").split(maxsplit=2)[1:]
    if not args:
        await message.answer("Usage: /adduser <telegram_id> [display_name]")
        return
    try:
        telegram_id = int(args[0])
    except ValueError:
        await message.answer("telegram_id must be an integer")
        return
    display_name = args[1] if len(args) > 1 else None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BACKEND}/api/bot/users",
            json={"telegram_id": telegram_id, "display_name": display_name, "added_by_telegram_id": message.from_user.id},
        )

    if resp.status_code == 201:
        await message.answer(f"Пользователь {telegram_id} добавлен.")
    elif resp.status_code == 409:
        await message.answer("Пользователь уже существует.")
    else:
        await message.answer(f"Ошибка: {resp.status_code}")


@router.message(Command("removeuser"))
async def cmd_removeuser(message: Message):
    """Usage: /removeuser <telegram_id>"""
    args = (message.text or "").split(maxsplit=1)[1:]
    if not args:
        await message.answer("Usage: /removeuser <telegram_id>")
        return
    try:
        telegram_id = int(args[0])
    except ValueError:
        await message.answer("telegram_id must be an integer")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{_BACKEND}/api/bot/users/{telegram_id}")

    if resp.status_code == 204:
        await message.answer(f"Пользователь {telegram_id} удалён.")
    else:
        await message.answer(f"Не найден или ошибка: {resp.status_code}")


@router.message(Command("users"))
async def cmd_users(message: Message):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/bot/users")

    if resp.status_code != 200:
        await message.answer("Ошибка получения списка.")
        return

    users = resp.json()
    if not users:
        await message.answer("Список пользователей пуст.")
        return

    lines = [f"• {u['telegram_id']} — {u.get('display_name') or 'без имени'}" for u in users]
    await message.answer("Пользователи:\n" + "\n".join(lines))
```

- [ ] **Step 7: Write `bot/handlers/misc.py`**

```python
import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот для каталога фильмов.\n\n"
        "Команды:\n"
        "/add — добавить фильм (или просто отправь название)\n"
        "/list — список каталога\n"
        "/find <текст> — поиск\n"
        "/random — случайный фильм\n"
        "/stats — статистика\n"
        "/watched <название> — отметить как просмотрено\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Команды бота:</b>\n\n"
        "<b>Добавление:</b>\n"
        "/add &lt;название&gt; — добавить по названию\n"
        "Отправь фото скриншота — добавить по скриншоту\n\n"
        "<b>Просмотр:</b>\n"
        "/list [category] — список\n"
        "/find &lt;текст&gt; — поиск\n"
        "/random [category] — случайный\n\n"
        "<b>Управление:</b>\n"
        "/watched, /watching, /unwatched &lt;название&gt;\n"
        "/delete &lt;название&gt;\n"
        "/edit &lt;название&gt;\n\n"
        "<b>Админ:</b>\n"
        "/adduser /removeuser /users\n"
        "/stats — статистика каталога",
        parse_mode="HTML",
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/stats")
    if resp.status_code != 200:
        await message.answer("Ошибка получения статистики.")
        return
    data = resp.json()
    total = data.get("total", 0)
    by_cat = data.get("by_category", {})
    by_status = data.get("by_watched_status", {})

    lines = [f"<b>Всего:</b> {total}"]
    if by_cat:
        lines.append("\n<b>По категориям:</b>")
        labels = {
            "cartoon": "Мультфильмы", "family_movie": "Семейные фильмы",
            "adult_movie": "Взрослые фильмы", "kids_series": "Детские сериалы",
            "adult_series": "Взрослые сериалы",
        }
        for k, v in by_cat.items():
            lines.append(f"  {labels.get(k, k)}: {v}")
    if by_status:
        lines.append("\n<b>По статусу:</b>")
        slabels = {"not_watched": "Не смотрели", "watching": "Смотрим", "watched": "Просмотрено"}
        for k, v in by_status.items():
            lines.append(f"  {slabels.get(k, k)}: {v}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("random"))
async def cmd_random(message: Message):
    args = (message.text or "").split(maxsplit=1)
    params = {}
    if len(args) > 1:
        params["category"] = args[1].strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media/random", params=params)

    if resp.status_code == 404:
        await message.answer("Ничего не найдено в каталоге.")
        return
    if resp.status_code != 200:
        await message.answer(f"Ошибка: {resp.status_code}")
        return

    m = resp.json()
    title = m.get("title_ru") or m.get("title", "")
    year = m.get("year", "")
    status_emoji = {"not_watched": "👀", "watching": "▶️", "watched": "✅"}.get(m.get("watched_status", ""), "")
    await message.answer(f"{status_emoji} <b>{title}</b> ({year})", parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.")
```

- [ ] **Step 8: Write `bot/main.py`**

```python
import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers import misc, users
from bot.middlewares.auth import WhitelistMiddleware

logging.basicConfig(level=logging.INFO)


async def bootstrap_admin(backend_url: str, admin_id: int) -> None:
    """If bot_users table is empty, add the initial admin."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{backend_url}/api/bot/users")
            if resp.status_code == 200 and len(resp.json()) == 0:
                await client.post(
                    f"{backend_url}/api/bot/users",
                    json={"telegram_id": admin_id, "display_name": "Admin"},
                )
                logging.info("Bootstrapped initial admin: %s", admin_id)
        except Exception as e:
            logging.warning("Bootstrap failed: %s", e)


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Whitelist middleware on all message and callback events
    dp.message.middleware(WhitelistMiddleware(backend_url=settings.backend_url))
    dp.callback_query.middleware(WhitelistMiddleware(backend_url=settings.backend_url))

    dp.include_router(misc.router)
    dp.include_router(users.router)

    # Import add/list/manage/status routers in later tasks
    # dp.include_router(add.router)
    # dp.include_router(list_.router)
    # dp.include_router(manage.router)
    # dp.include_router(status.router)

    await bootstrap_admin(settings.backend_url, settings.initial_admin_telegram_id)
    logging.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 9: Run middleware tests**

```bash
cd bot
python -m pytest tests/test_middleware.py -v
```

- [ ] **Step 10: Commit**

```bash
git add bot/ backend/app/routers/bot_router.py backend/app/main.py
git commit -m "Task 7: bot scaffolding, whitelist middleware, /api/bot/users routes, misc commands"
```

---

## Task 8: Bot — Add Flow (Text + Photo → Resolve → Confirm)

**Files:**
- Create: `bot/handlers/add.py`

**Interfaces:**
- Consumes: `states.AddMedia` FSM, backend /api/resolve, /api/resolve/screenshot, /api/media/confirm
- Produces: full add-media dialog with inline keyboards, photo support, category disambiguation

- [ ] **Step 1: Write `bot/handlers/add.py`**

```python
import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.states import AddMedia

router = Router()
_BACKEND = settings.backend_url

CATEGORY_LABELS = {
    "cartoon": "Мультфильм",
    "family_movie": "Семейный фильм",
    "adult_movie": "Взрослый фильм",
    "kids_series": "Детский сериал",
    "adult_series": "Взрослый сериал",
}

SUBTYPE_LABELS = {
    "disney": "Disney",
    "pixar": "Pixar",
    "soviet": "Советский",
    "russian": "Российский",
    "other": "Другой",
}


def _candidate_keyboard(candidates: list[dict], show_other: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for i, c in enumerate(candidates):
        label = f"{c['title']} ({c.get('year') or '?'})"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"candidate:{i}")])
    if show_other:
        buttons.append([InlineKeyboardButton(text="Это другое", callback_data="candidate:other")])
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="candidate:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"category:{key}")]
        for key, label in CATEGORY_LABELS.items()
    ]
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="candidate:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _subtype_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"subtype:{key}")]
        for key, label in SUBTYPE_LABELS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Добавить", callback_data="confirm:yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no"),
        ]
    ])


async def _resolve_and_show(message: Message, state: FSMContext, query: str = None, image_bytes: bytes = None):
    """Call backend resolve and display candidates."""
    await message.answer("🔍 Ищу в TMDB...")

    async with httpx.AsyncClient() as client:
        if image_bytes:
            resp = await client.post(
                f"{_BACKEND}/api/resolve/screenshot",
                files={"file": ("screenshot.jpg", image_bytes, "image/jpeg")},
                timeout=30,
            )
        else:
            resp = await client.post(f"{_BACKEND}/api/resolve", json={"query": query}, timeout=15)

    if resp.status_code != 200:
        await message.answer(f"Ошибка поиска: {resp.status_code}")
        await state.clear()
        return

    candidates = resp.json()
    if not candidates:
        await message.answer("Ничего не найдено. Попробуйте другое название.")
        await state.clear()
        return

    await state.update_data(candidates=candidates)
    await state.set_state(AddMedia.showing_candidates)

    if len(candidates) == 1:
        c = candidates[0]
        text = (
            f"<b>Найдено:</b> {c['title']} ({c.get('year') or '?'})\n"
            f"{c.get('description', '')[:200]}"
        )
        await message.answer(text, reply_markup=_confirm_keyboard(), parse_mode="HTML")
        await state.update_data(selected_index=0)
    else:
        dq = candidates[0].get("disambiguation_question") or "Какой из вариантов вы имели в виду?"
        text = f"{dq}\n"
        await message.answer(text, reply_markup=_candidate_keyboard(candidates), parse_mode="HTML")


# /add command
@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    args = (message.text or "").split(maxsplit=1)
    if len(args) > 1 and args[1].strip():
        await _resolve_and_show(message, state, query=args[1].strip())
    else:
        await message.answer("Введите название фильма или сериала:")
        await state.set_state(AddMedia.waiting_title)


# Plain text when in waiting_title state
@router.message(AddMedia.waiting_title, F.text)
async def receive_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Введите название.")
        return
    await _resolve_and_show(message, state, query=title)


# Plain text messages (not in state) — treat as implicit /add
@router.message(F.text & ~F.text.startswith("/"))
async def implicit_add(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await _resolve_and_show(message, state, query=message.text.strip())


# Photo message — screenshot mode
@router.message(F.photo)
async def receive_photo(message: Message, state: FSMContext):
    await message.answer("📷 Обрабатываю скриншот...")
    photo = message.photo[-1]  # largest size
    file = await message.bot.get_file(photo.file_id)
    downloaded = await message.bot.download_file(file.file_path)
    image_bytes = downloaded.read() if hasattr(downloaded, "read") else bytes(downloaded)
    await _resolve_and_show(message, state, image_bytes=image_bytes)


# Candidate selection callback
@router.callback_query(F.data.startswith("candidate:"), AddMedia.showing_candidates)
async def on_candidate_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    choice = callback.data.split(":", 1)[1]

    if choice == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        return

    if choice == "other":
        await state.set_state(AddMedia.waiting_title)
        await callback.message.edit_text("Введите другое название:")
        return

    idx = int(choice)
    data = await state.get_data()
    candidates = data["candidates"]
    selected = candidates[idx]
    await state.update_data(selected_index=idx)

    # Show confirmation card
    text = (
        f"<b>{selected['title']}</b> ({selected.get('year') or '?'})\n"
        f"{selected.get('description', '')[:200]}\n\n"
        f"Добавить в каталог?"
    )
    await callback.message.edit_text(text, reply_markup=_confirm_keyboard(), parse_mode="HTML")


# Confirm add (single candidate path or after candidate selection)
@router.callback_query(F.data == "confirm:yes", AddMedia.showing_candidates)
async def on_confirm_yes(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    candidates = data["candidates"]
    idx = data.get("selected_index", 0)
    selected = candidates[idx]

    # Check if category is already set (single-candidate pre-classification)
    category = selected.get("category")
    if category:
        await state.update_data(selected_category=category, selected_subtype=selected.get("cartoon_subtype"))
        await _do_confirm(callback.message, state, selected, category, selected.get("cartoon_subtype"))
    else:
        await state.set_state(AddMedia.confirming_category)
        await callback.message.edit_text(
            f"Выберите категорию для <b>{selected['title']}</b>:",
            reply_markup=_category_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "confirm:no")
async def on_confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Отменено.")


# Category selection
@router.callback_query(F.data.startswith("category:"), AddMedia.confirming_category)
async def on_category_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    category = callback.data.split(":", 1)[1]
    await state.update_data(selected_category=category)

    if category == "cartoon":
        await state.set_state(AddMedia.confirming_add)
        await callback.message.edit_text("Выберите тип мультфильма:", reply_markup=_subtype_keyboard())
    else:
        data = await state.get_data()
        candidates = data["candidates"]
        selected = candidates[data.get("selected_index", 0)]
        await _do_confirm(callback.message, state, selected, category, None)


# Subtype selection (cartoons only)
@router.callback_query(F.data.startswith("subtype:"), AddMedia.confirming_add)
async def on_subtype_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    subtype = callback.data.split(":", 1)[1]
    data = await state.get_data()
    candidates = data["candidates"]
    selected = candidates[data.get("selected_index", 0)]
    category = data.get("selected_category", "cartoon")
    await _do_confirm(callback.message, state, selected, category, subtype)


async def _do_confirm(message, state: FSMContext, candidate: dict, category: str, cartoon_subtype: str | None):
    """POST /api/media/confirm and show result."""
    await state.clear()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BACKEND}/api/media/confirm",
            json={
                "tmdb_id": candidate["tmdb_id"],
                "media_type": candidate["media_type"],
                "category": category,
                "cartoon_subtype": cartoon_subtype,
                "source": "telegram_text",
            },
            timeout=30,
        )

    if resp.status_code == 201:
        media = resp.json()
        title = media.get("title_ru") or media.get("title", "")
        year = media.get("year", "")
        cat_label = CATEGORY_LABELS.get(media.get("category", ""), media.get("category", ""))
        await message.edit_text(
            f"✅ <b>{title}</b> ({year}) добавлен!\nКатегория: {cat_label}",
            parse_mode="HTML",
        )
    else:
        await message.edit_text(f"Ошибка добавления: {resp.status_code}\n{resp.text[:200]}")
```

- [ ] **Step 2: Register add router in `bot/main.py`**

Uncomment or add:
```python
from bot.handlers import add as add_handler
dp.include_router(add_handler.router)
```

- [ ] **Step 3: Manual smoke test**

Run bot locally:
```bash
cd bot
TELEGRAM_BOT_TOKEN=... INITIAL_ADMIN_TELEGRAM_ID=... BACKEND_URL=http://localhost:8000 python main.py
```

Test:
- Send "Toy Story" → expect disambiguation or single result card → confirm → success message
- Send a screenshot of a movie poster → expect extraction + candidates
- Send /cancel mid-flow → state clears

- [ ] **Step 4: Commit**

```bash
git add bot/handlers/add.py bot/main.py
git commit -m "Task 8: bot add flow — text/photo resolve, inline candidate selection, category confirm"
```

---

## Task 9: Bot — Catalog Commands (/list, /find, /delete, /edit, /watched)

**Files:**
- Create: `bot/handlers/list_.py`
- Create: `bot/handlers/manage.py`
- Create: `bot/handlers/status.py`

**Interfaces:**
- Consumes: backend GET/PATCH/DELETE /api/media endpoints
- Produces: /list, /find, /delete, /edit, /watched, /watching, /unwatched commands

- [ ] **Step 1: Write `bot/handlers/list_.py`**

```python
import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url

STATUS_EMOJI = {"not_watched": "👀", "watching": "▶️", "watched": "✅"}


def _pagination_keyboard(page: int, total: int, page_size: int, prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"{prefix}:page:{page - 1}"))
    if page * page_size < total:
        row.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"{prefix}:page:{page + 1}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def _format_list(items: list[dict], page: int, total: int, page_size: int) -> str:
    lines = [f"<b>Каталог</b> (всего {total}):"]
    for m in items:
        title = m.get("title_ru") or m.get("title", "")
        year = m.get("year", "")
        emoji = STATUS_EMOJI.get(m.get("watched_status", ""), "")
        lines.append(f"{emoji} {title} ({year})")
    lines.append(f"\nСтраница {page}")
    return "\n".join(lines)


@router.message(Command("list"))
async def cmd_list(message: Message):
    args = (message.text or "").split(maxsplit=1)
    params = {"page": 1, "page_size": 10}
    if len(args) > 1:
        params["category"] = args[1].strip()
    prefix = f"list:{params.get('category', '')}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media", params=params)

    if resp.status_code != 200:
        await message.answer(f"Ошибка: {resp.status_code}")
        return

    data = resp.json()
    text = _format_list(data["items"], 1, data["total"], 10)
    kb = _pagination_keyboard(1, data["total"], 10, prefix)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^list:.*:page:\d+$"))
async def on_list_page(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split(":")
    # format: list:<category>:page:<n>
    category = parts[1]
    page = int(parts[3])
    params = {"page": page, "page_size": 10}
    if category:
        params["category"] = category
    prefix = f"list:{category}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media", params=params)

    if resp.status_code != 200:
        await callback.message.edit_text(f"Ошибка: {resp.status_code}")
        return

    data = resp.json()
    text = _format_list(data["items"], page, data["total"], 10)
    kb = _pagination_keyboard(page, data["total"], 10, prefix)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("find"))
async def cmd_find(message: Message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /find <текст поиска>")
        return
    query = args[1].strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media", params={"search": query, "page_size": 20})

    if resp.status_code != 200:
        await message.answer(f"Ошибка: {resp.status_code}")
        return

    data = resp.json()
    if not data["items"]:
        await message.answer("Ничего не найдено.")
        return

    text = _format_list(data["items"], 1, data["total"], 20)
    await message.answer(text, parse_mode="HTML")
```

- [ ] **Step 2: Write `bot/handlers/manage.py`**

```python
import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import settings
from bot.states import DeleteConfirm, EditMedia

router = Router()
_BACKEND = settings.backend_url


async def _search_media(query: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media", params={"search": query, "page_size": 5})
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
        resp = await client.get(f"{_BACKEND}/api/media/{media_id}")
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
        resp = await client.delete(f"{_BACKEND}/api/media/{media_id}")
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
        )
    if resp.status_code == 200:
        await message.answer("✅ Обновлено.")
    else:
        await message.answer(f"Ошибка: {resp.status_code}")
```

- [ ] **Step 3: Write `bot/handlers/status.py`**

```python
import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings

router = Router()
_BACKEND = settings.backend_url


async def _set_status(message: Message, status: str):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"Usage: /{status.replace('_', '')} <название>")
        return
    query = args[1].strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{_BACKEND}/api/media", params={"search": query, "page_size": 1})

    if resp.status_code != 200 or not resp.json().get("items"):
        await message.answer("Не найдено.")
        return

    m = resp.json()["items"][0]
    async with httpx.AsyncClient() as client:
        resp = await client.patch(f"{_BACKEND}/api/media/{m['id']}", json={"watched_status": status})

    if resp.status_code == 200:
        title = m.get("title_ru") or m.get("title")
        labels = {"not_watched": "не просмотрено", "watching": "смотрим", "watched": "просмотрено"}
        await message.answer(f"✅ <b>{title}</b> — {labels[status]}", parse_mode="HTML")
    else:
        await message.answer(f"Ошибка: {resp.status_code}")


@router.message(Command("watched"))
async def cmd_watched(message: Message):
    await _set_status(message, "watched")


@router.message(Command("watching"))
async def cmd_watching(message: Message):
    await _set_status(message, "watching")


@router.message(Command("unwatched"))
async def cmd_unwatched(message: Message):
    await _set_status(message, "not_watched")
```

- [ ] **Step 4: Register all handlers in `bot/main.py`**

```python
from bot.handlers import list_ as list_handler, manage as manage_handler, status as status_handler

dp.include_router(list_handler.router)
dp.include_router(manage_handler.router)
dp.include_router(status_handler.router)
```

- [ ] **Step 5: Manual smoke test and commit**

```bash
# Test commands in Telegram:
# /list → paginated list
# /find Toy → search results
# /delete Toy Story → confirm dialog → deleted
# /edit Toy Story → field selection → update
# /watched Toy Story → status updated

git add bot/handlers/list_.py bot/handlers/manage.py bot/handlers/status.py bot/main.py
git commit -m "Task 9: bot /list, /find, /delete, /edit, /watched commands"
```

---

## Task 10: Web UI Foundation — Vite + React, Auth, Types

**Files:**
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tailwind.config.js`
- Create: `web/src/types.ts`
- Create: `web/src/api.ts`
- Create: `web/src/pages/Login.tsx`
- Create: `web/src/pages/Layout.tsx`
- Create: `web/src/App.tsx`
- Test: `web/src/api.test.ts`

**Interfaces:**
- Consumes: backend /api/auth/*, /api/media, /api/stats, /api/resolve, /api/media/confirm
- Produces: React SPA with login gate, typed API client, React Router layout

- [ ] **Step 1: Initialize Vite project and install dependencies**

```bash
cd web
npm create vite@latest . -- --template react-ts --force
npm install
npm install -D tailwindcss @tailwindcss/forms postcss autoprefixer
npx tailwindcss init -p
npm install react-router-dom
npm install -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom
```

- [ ] **Step 2: Write `web/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [require("@tailwindcss/forms")],
};
```

Add to `web/src/index.css` (replace contents):
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 3: Write `web/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

Create `web/src/test-setup.ts`:
```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 4: Write `web/src/types.ts`**

```typescript
export type MediaType = "movie" | "cartoon" | "series";

export type MediaCategory =
  | "kids_series"
  | "adult_series"
  | "family_movie"
  | "adult_movie"
  | "cartoon";

export type CartoonSubtype = "disney" | "pixar" | "soviet" | "russian" | "other";

export type WatchedStatus = "not_watched" | "watching" | "watched";

export type MediaSource = "telegram_text" | "telegram_screenshot" | "web_ui";

export interface Media {
  id: string;
  title: string;
  title_ru: string | null;
  year: number | null;
  description: string | null;
  poster_url: string | null;
  type: MediaType;
  category: MediaCategory;
  cartoon_subtype: CartoonSubtype | null;
  genres: string[];
  actors: string[];
  external_ids: Record<string, unknown>;
  rating_external: number | null;
  added_at: string;
  watched_at: string | null;
  watched_status: WatchedStatus;
  source: MediaSource;
  added_by: string | null;
  notes: string | null;
}

export interface MediaListResponse {
  items: Media[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  total: number;
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  by_watched_status: Record<string, number>;
}

export interface Candidate {
  tmdb_id: number;
  media_type: string;
  title: string;
  title_ru: string | null;
  year: number | null;
  description: string | null;
  poster_url: string | null;
  genres: string[];
  rating: number | null;
  disambiguation_question: string | null;
}

export interface MediaUpdate {
  title?: string;
  title_ru?: string;
  year?: number;
  description?: string;
  category?: MediaCategory;
  cartoon_subtype?: CartoonSubtype | null;
  watched_status?: WatchedStatus;
  notes?: string;
}
```

- [ ] **Step 5: Write `web/src/api.ts`**

```typescript
import type { Candidate, Media, MediaListResponse, MediaUpdate, StatsResponse } from "./types";
import type { MediaCategory, MediaSource, CartoonSubtype } from "./types";

const BASE = "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (resp.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new Error(`${resp.status}: ${text}`);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  auth: {
    login: (login: string, password: string) =>
      request<{ ok: boolean }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ login, password }),
      }),
    logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
    me: () => request<{ login: string }>("/auth/me"),
  },

  media: {
    list: (params: {
      page?: number;
      page_size?: number;
      category?: string;
      type?: string;
      watched_status?: string;
      search?: string;
    } = {}) => {
      const qs = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params)
            .filter(([, v]) => v !== undefined && v !== "")
            .map(([k, v]) => [k, String(v)])
        )
      ).toString();
      return request<MediaListResponse>(`/media${qs ? `?${qs}` : ""}`);
    },
    get: (id: string) => request<Media>(`/media/${id}`),
    patch: (id: string, data: MediaUpdate) =>
      request<Media>(`/media/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/media/${id}`, { method: "DELETE" }),
    random: (params: { category?: string; type?: string } = {}) => {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v))
      ).toString();
      return request<Media>(`/media/random${qs ? `?${qs}` : ""}`);
    },
    stats: () => request<StatsResponse>("/stats"),
  },

  resolve: {
    byText: (query: string) =>
      request<Candidate[]>("/resolve", { method: "POST", body: JSON.stringify({ query }) }),
    byScreenshot: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return fetch(`${BASE}/resolve/screenshot`, { method: "POST", credentials: "include", body: fd }).then(
        (r) => (r.ok ? r.json() as Promise<Candidate[]> : Promise.reject(new Error(`${r.status}`)))
      );
    },
    confirm: (data: {
      tmdb_id: number;
      media_type: string;
      category: MediaCategory;
      cartoon_subtype?: CartoonSubtype | null;
      source: MediaSource;
      notes?: string;
    }) => request<Media>("/media/confirm", { method: "POST", body: JSON.stringify(data) }),
  },
};
```

- [ ] **Step 6: Write `web/src/api.test.ts`**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Reset location mock
Object.defineProperty(window, "location", {
  value: { href: "" },
  writable: true,
});

describe("api.media.list", () => {
  beforeEach(() => { mockFetch.mockReset(); });

  it("builds correct URL with no params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 20 }),
    });
    const { api } = await import("./api");
    await api.media.list();
    expect(mockFetch).toHaveBeenCalledWith("/api/media", expect.any(Object));
  });

  it("appends query params correctly", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 20 }),
    });
    const { api } = await import("./api");
    await api.media.list({ page: 2, category: "cartoon" });
    const url = (mockFetch.mock.calls[0][0] as string);
    expect(url).toContain("page=2");
    expect(url).toContain("category=cartoon");
  });

  it("redirects to /login on 401", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
    const { api } = await import("./api");
    await expect(api.media.list()).rejects.toThrow("Unauthorized");
    expect(window.location.href).toBe("/login");
  });
});
```

- [ ] **Step 7: Write `web/src/pages/Login.tsx`**

```tsx
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Login() {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.auth.login(login, password);
      navigate("/");
    } catch (err) {
      setError("Неверный логин или пароль");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-sm w-full space-y-6 p-8 bg-white rounded-xl shadow">
        <h1 className="text-2xl font-bold text-center text-gray-900">Каталог фильмов</h1>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Логин</label>
            <input
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "Вход..." : "Войти"}
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Write `web/src/pages/Layout.tsx` and `web/src/App.tsx`**

`web/src/pages/Layout.tsx`:
```tsx
import { Link, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Layout() {
  const navigate = useNavigate();

  async function handleLogout() {
    await api.auth.logout().catch(() => {});
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-indigo-600 text-lg">🎬 Каталог</span>
          <Link to="/" className="text-sm text-gray-700 hover:text-indigo-600">Каталог</Link>
          <Link to="/stats" className="text-sm text-gray-700 hover:text-indigo-600">Статистика</Link>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-600"
        >
          Выйти
        </button>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
```

`web/src/App.tsx`:
```tsx
import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import Login from "./pages/Login";
import Layout from "./pages/Layout";

// Lazy imports (created in Tasks 11-12)
import { lazy, Suspense } from "react";
const Catalog = lazy(() => import("./pages/Catalog"));
const Stats = lazy(() => import("./pages/Stats"));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<"loading" | "ok" | "fail">("loading");

  useEffect(() => {
    api.auth.me().then(() => setAuth("ok")).catch(() => setAuth("fail"));
  }, []);

  if (auth === "loading") return <div className="p-4 text-gray-500">Загрузка...</div>;
  if (auth === "fail") return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={
              <Suspense fallback={<div>Загрузка...</div>}>
                <Catalog />
              </Suspense>
            }
          />
          <Route
            path="stats"
            element={
              <Suspense fallback={<div>Загрузка...</div>}>
                <Stats />
              </Suspense>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

Create placeholder `web/src/pages/Catalog.tsx` and `web/src/pages/Stats.tsx` (full versions in Tasks 11-12):
```tsx
// web/src/pages/Catalog.tsx — placeholder
export default function Catalog() { return <div>Catalog (Task 11)</div>; }

// web/src/pages/Stats.tsx — placeholder  
export default function Stats() { return <div>Stats (Task 12)</div>; }
```

- [ ] **Step 9: Run API tests**

```bash
cd web
npm test
```

- [ ] **Step 10: Commit**

```bash
git add web/
git commit -m "Task 10: web Vite/React/TypeScript foundation, auth pages, typed API client"
```

---

## Task 11: Web UI — Catalog Page + Add Modal

**Files:**
- Create: `web/src/components/MediaCard.tsx`
- Create: `web/src/components/FilterBar.tsx`
- Create: `web/src/components/Pagination.tsx`
- Create: `web/src/components/AddMediaModal.tsx`
- Create: `web/src/pages/Catalog.tsx` (replace placeholder)

**Interfaces:**
- Consumes: `api.media.list`, `api.resolve.byText`, `api.resolve.confirm`, types from types.ts
- Produces: browsable, filterable catalog page with add-media flow

- [ ] **Step 1: Write `web/src/components/MediaCard.tsx`**

```tsx
import type { Media } from "../types";

const CATEGORY_LABELS: Record<string, string> = {
  cartoon: "Мультфильм",
  family_movie: "Семейный фильм",
  adult_movie: "Взрослый фильм",
  kids_series: "Детский сериал",
  adult_series: "Взрослый сериал",
};

const STATUS_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  not_watched: { emoji: "👀", label: "Не смотрели", color: "bg-gray-100 text-gray-600" },
  watching: { emoji: "▶️", label: "Смотрим", color: "bg-blue-100 text-blue-700" },
  watched: { emoji: "✅", label: "Просмотрено", color: "bg-green-100 text-green-700" },
};

interface Props {
  media: Media;
  onEdit?: (media: Media) => void;
}

export default function MediaCard({ media, onEdit }: Props) {
  const title = media.title_ru || media.title;
  const status = STATUS_CONFIG[media.watched_status] ?? STATUS_CONFIG.not_watched;
  const catLabel = CATEGORY_LABELS[media.category] ?? media.category;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col">
      {media.poster_url ? (
        <img
          src={media.poster_url}
          alt={title}
          className="w-full h-48 object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-48 bg-gray-200 flex items-center justify-center text-gray-400 text-4xl">
          🎬
        </div>
      )}
      <div className="p-3 flex flex-col gap-1 flex-1">
        <h3 className="font-semibold text-gray-900 text-sm leading-tight line-clamp-2">{title}</h3>
        <p className="text-xs text-gray-400">{media.year ?? "—"}</p>
        <div className="flex flex-wrap gap-1 mt-auto pt-2">
          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">{catLabel}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}>
            {status.emoji} {status.label}
          </span>
        </div>
        {onEdit && (
          <button
            onClick={() => onEdit(media)}
            className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 text-left"
          >
            Редактировать
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `web/src/components/FilterBar.tsx`**

```tsx
interface Filters {
  category: string;
  type: string;
  watched_status: string;
  search: string;
}

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

const CATEGORIES = [
  { value: "", label: "Все категории" },
  { value: "cartoon", label: "Мультфильм" },
  { value: "family_movie", label: "Семейный фильм" },
  { value: "adult_movie", label: "Взрослый фильм" },
  { value: "kids_series", label: "Детский сериал" },
  { value: "adult_series", label: "Взрослый сериал" },
];

const TYPES = [
  { value: "", label: "Все типы" },
  { value: "movie", label: "Фильм" },
  { value: "cartoon", label: "Мультфильм" },
  { value: "series", label: "Сериал" },
];

const STATUSES = [
  { value: "", label: "Любой статус" },
  { value: "not_watched", label: "Не смотрели" },
  { value: "watching", label: "Смотрим" },
  { value: "watched", label: "Просмотрено" },
];

export default function FilterBar({ filters, onChange }: Props) {
  function set(key: keyof Filters, value: string) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="flex flex-wrap gap-3 items-center">
      <input
        type="search"
        placeholder="Поиск..."
        value={filters.search}
        onChange={(e) => set("search", e.target.value)}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-indigo-500 focus:border-indigo-500 w-48"
      />
      <select
        value={filters.category}
        onChange={(e) => set("category", e.target.value)}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
      >
        {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
      <select
        value={filters.type}
        onChange={(e) => set("type", e.target.value)}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
      >
        {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
      </select>
      <select
        value={filters.watched_status}
        onChange={(e) => set("watched_status", e.target.value)}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
      >
        {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>
    </div>
  );
}
```

- [ ] **Step 3: Write `web/src/components/Pagination.tsx`**

```tsx
interface Props {
  page: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, total, pageSize, onChange }: Props) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center gap-3 justify-center mt-6">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
      >
        ◀ Назад
      </button>
      <span className="text-sm text-gray-600">
        {page} / {totalPages}
      </span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
      >
        Вперёд ▶
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Write `web/src/components/AddMediaModal.tsx`**

```tsx
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { Candidate, MediaCategory, CartoonSubtype } from "../types";
import { api } from "../api";

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  cartoon: "Мультфильм",
  family_movie: "Семейный фильм",
  adult_movie: "Взрослый фильм",
  kids_series: "Детский сериал",
  adult_series: "Взрослый сериал",
};

const SUBTYPE_LABELS: Record<string, string> = {
  disney: "Disney",
  pixar: "Pixar",
  soviet: "Советский",
  russian: "Российский",
  other: "Другой",
};

type Step = "search" | "candidates" | "confirm";

export default function AddMediaModal({ onClose, onAdded }: Props) {
  const [step, setStep] = useState<Step>("search");
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [category, setCategory] = useState<MediaCategory>("family_movie");
  const [subtype, setSubtype] = useState<CartoonSubtype | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced search
  const search = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError("");
    try {
      const results = await api.resolve.byText(q);
      setCandidates(results);
      setStep("candidates");
    } catch (e) {
      setError(`Ошибка поиска: ${e}`);
    } finally {
      setLoading(false);
    }
  }, []);

  function handleQueryChange(val: string) {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(val), 500);
  }

  function selectCandidate(c: Candidate) {
    setSelected(c);
    // Pre-fill category if only one candidate was returned with classification
    setStep("confirm");
  }

  async function handleConfirm(e: FormEvent) {
    e.preventDefault();
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      await api.resolve.confirm({
        tmdb_id: selected.tmdb_id,
        media_type: selected.media_type,
        category,
        cartoon_subtype: category === "cartoon" ? subtype : null,
        source: "web_ui",
        notes: notes || undefined,
      });
      onAdded();
      onClose();
    } catch (e) {
      setError(`Ошибка: ${e}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Добавить в каталог</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">{error}</div>
          )}

          {/* Step 1: Search */}
          {step === "search" && (
            <div>
              <input
                type="text"
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                placeholder="Введите название фильма или сериала..."
                autoFocus
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
              {loading && <p className="text-sm text-gray-500 mt-2">Поиск...</p>}
            </div>
          )}

          {/* Step 2: Candidates */}
          {step === "candidates" && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600">
                  {candidates[0]?.disambiguation_question || "Выберите нужный вариант:"}
                </p>
                <button onClick={() => setStep("search")} className="text-xs text-indigo-600">← Назад</button>
              </div>
              <div className="space-y-2">
                {candidates.map((c) => (
                  <button
                    key={`${c.tmdb_id}-${c.media_type}`}
                    onClick={() => selectCandidate(c)}
                    className="w-full text-left flex gap-3 p-2 rounded-lg border border-gray-200 hover:border-indigo-400 hover:bg-indigo-50 transition"
                  >
                    {c.poster_url && (
                      <img src={c.poster_url} alt={c.title} className="w-12 h-16 object-cover rounded" />
                    )}
                    <div>
                      <p className="font-medium text-sm">{c.title}</p>
                      <p className="text-xs text-gray-400">{c.year ?? "—"}</p>
                      <p className="text-xs text-gray-500 line-clamp-2">{c.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Confirm */}
          {step === "confirm" && selected && (
            <form onSubmit={handleConfirm} className="space-y-4">
              <div className="flex gap-3">
                {selected.poster_url && (
                  <img src={selected.poster_url} alt={selected.title} className="w-16 h-24 object-cover rounded" />
                )}
                <div>
                  <p className="font-semibold">{selected.title}</p>
                  <p className="text-sm text-gray-400">{selected.year ?? "—"}</p>
                  <p className="text-xs text-gray-500 line-clamp-3 mt-1">{selected.description}</p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Категория</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as MediaCategory)}
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
                >
                  {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>

              {category === "cartoon" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Тип мультфильма</label>
                  <select
                    value={subtype ?? ""}
                    onChange={(e) => setSubtype((e.target.value as CartoonSubtype) || null)}
                    className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
                  >
                    <option value="">— Выбрать —</option>
                    {Object.entries(SUBTYPE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Заметки (необязательно)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setStep("candidates")}
                  className="flex-1 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
                >
                  ← Назад
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? "Добавление..." : "Добавить"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Write `web/src/pages/Catalog.tsx`**

```tsx
import { useCallback, useEffect, useRef, useState } from "react";
import type { Media } from "../types";
import { api } from "../api";
import MediaCard from "../components/MediaCard";
import FilterBar from "../components/FilterBar";
import Pagination from "../components/Pagination";
import AddMediaModal from "../components/AddMediaModal";
// EditMediaModal imported in Task 12
// import EditMediaModal from "../components/EditMediaModal";

interface Filters {
  category: string;
  type: string;
  watched_status: string;
  search: string;
}

const DEFAULT_FILTERS: Filters = { category: "", type: "", watched_status: "", search: "" };
const PAGE_SIZE = 24;

export default function Catalog() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Media[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Media | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (f: Filters, p: number) => {
    setLoading(true);
    setError("");
    try {
      const data = await api.media.list({ ...f, page: p, page_size: PAGE_SIZE });
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(`Ошибка загрузки: ${e}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => load(filters, page), filters.search ? 400 : 0);
  }, [filters, page, load]);

  function handleFilterChange(newFilters: Filters) {
    setFilters(newFilters);
    setPage(1);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <FilterBar filters={filters} onChange={handleFilterChange} />
        <button
          onClick={() => setShowAdd(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700"
        >
          + Добавить
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-12">Загрузка...</div>
      ) : items.length === 0 ? (
        <div className="text-center text-gray-400 py-12">Ничего не найдено</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {items.map((m) => (
            <MediaCard key={m.id} media={m} onEdit={setEditTarget} />
          ))}
        </div>
      )}

      <Pagination page={page} total={total} pageSize={PAGE_SIZE} onChange={setPage} />

      {showAdd && (
        <AddMediaModal
          onClose={() => setShowAdd(false)}
          onAdded={() => load(filters, page)}
        />
      )}

      {/* EditMediaModal wired up in Task 12 */}
      {editTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded p-4">
            <p>Edit modal — Task 12</p>
            <button onClick={() => setEditTarget(null)}>Закрыть</button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Verify in browser**

```bash
cd web
npm run dev
# Open http://localhost:5173
# Verify: login works, catalog lists items, filters work, add modal opens, new item appears after add
```

- [ ] **Step 7: Commit**

```bash
git add web/src/
git commit -m "Task 11: catalog page, MediaCard, FilterBar, Pagination, AddMediaModal"
```

---

## Task 12: Web UI — Edit Modal + Stats Page + README

**Files:**
- Create: `web/src/components/EditMediaModal.tsx`
- Create: `web/src/pages/Stats.tsx` (replace placeholder)
- Create: `README.md`

**Interfaces:**
- Consumes: `api.media.patch`, `api.media.stats`, `Media` type
- Produces: complete web UI, production README

- [ ] **Step 1: Write `web/src/components/EditMediaModal.tsx`**

```tsx
import { FormEvent, useState } from "react";
import type { CartoonSubtype, Media, MediaCategory, WatchedStatus } from "../types";
import { api } from "../api";

interface Props {
  media: Media;
  onClose: () => void;
  onSaved: (updated: Media) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  cartoon: "Мультфильм",
  family_movie: "Семейный фильм",
  adult_movie: "Взрослый фильм",
  kids_series: "Детский сериал",
  adult_series: "Взрослый сериал",
};

const SUBTYPE_LABELS: Record<string, string> = {
  disney: "Disney",
  pixar: "Pixar",
  soviet: "Советский",
  russian: "Российский",
  other: "Другой",
};

const STATUS_LABELS: Record<string, string> = {
  not_watched: "Не смотрели",
  watching: "Смотрим",
  watched: "Просмотрено",
};

export default function EditMediaModal({ media, onClose, onSaved }: Props) {
  const [titleRu, setTitleRu] = useState(media.title_ru ?? "");
  const [category, setCategory] = useState<MediaCategory>(media.category);
  const [subtype, setSubtype] = useState<CartoonSubtype | null>(media.cartoon_subtype);
  const [watchedStatus, setWatchedStatus] = useState<WatchedStatus>(media.watched_status);
  const [notes, setNotes] = useState(media.notes ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const updated = await api.media.patch(media.id, {
        title_ru: titleRu || undefined,
        category,
        cartoon_subtype: category === "cartoon" ? subtype : null,
        watched_status: watchedStatus,
        notes: notes || undefined,
      });
      onSaved(updated);
      onClose();
    } catch (e) {
      setError(`Ошибка: ${e}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Редактировать</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">{error}</div>
          )}

          <div>
            <p className="text-xs text-gray-400 mb-1">Оригинальное название</p>
            <p className="font-medium text-sm">{media.title} {media.year ? `(${media.year})` : ""}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Русское название</label>
            <input
              type="text"
              value={titleRu}
              onChange={(e) => setTitleRu(e.target.value)}
              placeholder={media.title}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Категория</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as MediaCategory)}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            >
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          {category === "cartoon" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Тип мультфильма</label>
              <select
                value={subtype ?? ""}
                onChange={(e) => setSubtype((e.target.value as CartoonSubtype) || null)}
                className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
              >
                <option value="">— Выбрать —</option>
                {Object.entries(SUBTYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Статус просмотра</label>
            <select
              value={watchedStatus}
              onChange={(e) => setWatchedStatus(e.target.value as WatchedStatus)}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            >
              {Object.entries(STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Заметки</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? "Сохранение..." : "Сохранить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire EditMediaModal into `web/src/pages/Catalog.tsx`**

Replace the placeholder edit block in `Catalog.tsx` with:

```tsx
// At top of file, add import:
import EditMediaModal from "../components/EditMediaModal";

// Replace the placeholder edit modal JSX block with:
{editTarget && (
  <EditMediaModal
    media={editTarget}
    onClose={() => setEditTarget(null)}
    onSaved={(updated) => {
      setItems((prev) => prev.map((m) => m.id === updated.id ? updated : m));
      setEditTarget(null);
    }}
  />
)}
```

- [ ] **Step 3: Write `web/src/pages/Stats.tsx`**

```tsx
import { useEffect, useState } from "react";
import type { StatsResponse } from "../types";
import { api } from "../api";

const CATEGORY_LABELS: Record<string, string> = {
  cartoon: "Мультфильмы",
  family_movie: "Семейные фильмы",
  adult_movie: "Взрослые фильмы",
  kids_series: "Детские сериалы",
  adult_series: "Взрослые сериалы",
};

const TYPE_LABELS: Record<string, string> = {
  movie: "Фильм",
  cartoon: "Мультфильм",
  series: "Сериал",
};

const STATUS_LABELS: Record<string, string> = {
  not_watched: "Не смотрели",
  watching: "Смотрим",
  watched: "Просмотрено",
};

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl shadow p-5 flex flex-col gap-1">
      <p className="text-3xl font-bold text-indigo-600">{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  );
}

function BarChart({ data, labels }: { data: Record<string, number>; labels: Record<string, string> }) {
  const max = Math.max(...Object.values(data), 1);
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([key, val]) => (
        <div key={key} className="flex items-center gap-3">
          <span className="text-sm text-gray-600 w-36 shrink-0">{labels[key] ?? key}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
            <div
              className="h-5 bg-indigo-500 rounded-full transition-all"
              style={{ width: `${(val / max) * 100}%` }}
            />
          </div>
          <span className="text-sm font-medium text-gray-700 w-8 text-right">{val}</span>
        </div>
      ))}
    </div>
  );
}

export default function Stats() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.media.stats()
      .then(setStats)
      .catch((e) => setError(`Ошибка: ${e}`))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center text-gray-400 py-12">Загрузка...</div>;
  if (error) return <div className="text-red-600 py-4">{error}</div>;
  if (!stats) return null;

  const watched = stats.by_watched_status["watched"] ?? 0;
  const notWatched = stats.by_watched_status["not_watched"] ?? 0;
  const watching = stats.by_watched_status["watching"] ?? 0;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Статистика</h1>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatTile label="Всего" value={stats.total} />
        <StatTile label="Просмотрено" value={watched} />
        <StatTile label="Смотрим" value={watching} />
        <StatTile label="Не смотрели" value={notWatched} />
      </div>

      <div className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">По категориям</h2>
        <BarChart data={stats.by_category} labels={CATEGORY_LABELS} />
      </div>

      <div className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">По типу</h2>
        <BarChart data={stats.by_type} labels={TYPE_LABELS} />
      </div>

      <div className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">По статусу просмотра</h2>
        <BarChart data={stats.by_watched_status} labels={STATUS_LABELS} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write `README.md`**

```markdown
# Movie Catalog

Personal movie/series/cartoon catalog with Telegram bot management and React web UI.

## Local development

### Prerequisites
- Docker + Docker Compose v2
- Node.js 20 (for web dev only)
- Python 3.12 (for backend dev only)

### Setup

```bash
cp .env.example .env
# Edit .env — fill in required values (see comments)

# Generate bcrypt password hash for web login:
python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpassword'))"
# Paste the output into WEB_USER_1_PASSWORD_HASH in .env
```

### Run everything

```bash
docker-compose up --build
```

- Backend API: http://localhost:8000
- Web UI: http://localhost (via Caddy, or set DOMAIN=localhost)
- MinIO console: http://localhost:9001

### Run backend in dev mode (hot reload)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql+asyncpg://catalog:changeme@localhost/moviecatalog \
uvicorn app.main:app --reload --port 8000
```

### Run web in dev mode (hot reload + API proxy)

```bash
cd web
npm install
npm run dev
# Open http://localhost:5173
```

### Run tests

```bash
# Backend
cd backend && python -m pytest -v

# Web
cd web && npm test
```

## Production deploy (VPS)

### 1. Point your domain DNS to the VPS IP

### 2. Clone repo on VPS

```bash
git clone <repo-url> /opt/movie-catalog
cd /opt/movie-catalog
```

### 3. Configure environment

```bash
cp .env.example .env
nano .env
# Set: DOMAIN, POSTGRES_PASSWORD, JWT_SECRET (long random string),
#      TELEGRAM_BOT_TOKEN, INITIAL_ADMIN_TELEGRAM_ID,
#      OPENAI_API_KEY, TMDB_API_KEY,
#      MINIO_ROOT_USER, MINIO_ROOT_PASSWORD,
#      WEB_USER_1_LOGIN, WEB_USER_1_PASSWORD_HASH
```

### 4. Start

```bash
docker-compose up -d --build
```

Caddy automatically obtains a TLS certificate from Let's Encrypt for your domain.

### 5. Run database migrations

```bash
docker-compose exec backend alembic upgrade head
```

### 6. Verify

```bash
docker-compose ps        # all services Up
docker-compose logs -f   # watch logs
```

## Architecture

```
Caddy (TLS, ports 80/443)
  ├── /api/* → backend:8000 (FastAPI)
  └── /* → web:80 (nginx serving React SPA)

backend → postgres:5432
backend → minio:9000

bot → backend:8000 (HTTP, internal network only)
```

## Adding users to the Telegram bot

The initial admin is set via `INITIAL_ADMIN_TELEGRAM_ID` in `.env`.
The admin can add more users via:

```
/adduser <telegram_id> [display_name]
```

Get a Telegram user's ID by forwarding their message to @userinfobot.
```

- [ ] **Step 5: Final end-to-end verification in browser**

```bash
docker-compose up --build

# Test checklist:
# 1. Open http://localhost → redirected to /login
# 2. Login with WEB_USER_1 credentials → catalog page loads
# 3. Catalog shows items (or empty state if fresh DB)
# 4. Click "+ Добавить" → type "Toy Story" → wait 500ms → candidates appear
# 5. Select candidate → confirm → card appears in catalog
# 6. Click "Редактировать" on a card → change watched_status to "watched" → save → card updates
# 7. Navigate to Статистика → counts are correct
# 8. Open Telegram → send "Toy Story" to bot → resolve flow works → item added
# 9. /stats in bot → correct numbers
# 10. /list in bot → items paginate
```

- [ ] **Step 6: Final commit**

```bash
git add web/src/components/EditMediaModal.tsx web/src/pages/Stats.tsx web/src/pages/Catalog.tsx README.md
git commit -m "Task 12: EditMediaModal, Stats page, README — MVP complete"
```

---

*Plan complete. All 12 tasks are self-contained and independently executable. Start from Task 1 and proceed in order — each task produces artifacts that the next task depends on.*
