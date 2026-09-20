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
