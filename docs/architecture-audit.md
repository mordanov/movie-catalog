# Architecture Design Audit

## Scope and current design

The application is a modular monolith composed of a FastAPI backend, React SPA, Telegram bot, PostgreSQL, MinIO, nginx, and Caddy (`README.md:106-115`, `docker-compose.yml:1-96`). This is a sensible MVP topology: the web UI and bot share one domain API, while TMDB, OpenAI, and S3 concerns are already isolated in service modules.

## Strengths

- Clear runtime separation and named data volumes (`docker-compose.yml:3-19`, `docker-compose.yml:91-95`).
- Typed SQLAlchemy models and Pydantic request/response schemas (`backend/app/models.py:43-100`, `backend/app/schemas.py:8-67`).
- Bounded pagination and explicit sort allow predictable catalog reads (`backend/app/routers/media_router.py:23-66`).
- CI covers lint, backend tests, frontend tests, and Compose validation (`.github/workflows/ci.yml:1-75`).

## Findings

| Priority | Finding | Evidence | Impact |
|---|---|---|---|
| P0 | `confirm` is a large synchronous orchestration path: provider lookup, translation, poster download, storage, ORM construction, and commit happen in one request. | `backend/app/routers/resolve_router.py:89-146` | Slow or failed vendors directly affect writes; retries, testing, and rollback are difficult. |
| P1 | Database migrations run inside every backend container startup. | `backend/Dockerfile:11-13` | Replicas can race and an incompatible migration can prevent the application from starting. |
| P1 | `/api/health` is always successful and the backend has no Compose healthcheck. | `backend/app/main.py:16-20`, `docker-compose.yml:35-55` | Traffic can be accepted while the database or dependencies are unavailable. |
| P1 | Provider identity is not unique and domain invariants are not enforced in the database. | `backend/app/models.py:43-100` | Web and bot retries can create duplicates or invalid category/subtype combinations. |
| P1 | External HTTP/AI calls lack a shared timeout, retry, circuit-breaker, and cost policy. | `backend/app/services/tmdb.py:13-52`, `backend/app/services/storage.py:11-13`, `backend/app/services/openai_client.py:45-110` | Vendor outages become user-facing failures and repeated requests can increase spend. |
| P2 | Bot whitelist state is process-local and cached in memory. | `bot/middlewares/auth.py:8-20` | Restart loses cache state and horizontal scaling requires coordination. |

## Recommended target

Keep the modular monolith, but introduce explicit application services and repositories. Routers should handle transport and authorization; services should own ingestion and mutation workflows; infrastructure adapters should own vendor clients and consistent error/timeout policy. Move poster ingestion, translation, and AI classification to a background job when latency or reliability requires it.

## Acceptance criteria

- `confirm` is idempotent for `(provider, provider_id, media_type)`.
- Vendor failures cannot leave partial records or orphaned objects.
- Liveness and database readiness are separate.
- Database constraints enforce provider identity and category invariants.
- Migrations run as an observable deployment step, not application startup.

