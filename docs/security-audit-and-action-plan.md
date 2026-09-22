# Security Audit and Action Plan

## Assessment basis

This is a source review of authentication, authorization, input handling, uploads, external calls, bot rendering, and deployment configuration. It is not a penetration test, dependency CVE scan, or cloud configuration assessment.

## Findings

| Severity | Finding | Evidence | Risk |
|---|---|---|---|
| HIGH | `BOT_SECRET` is an alternate credential for every endpoint protected by `get_current_user`, including destructive and user-management operations. | `backend/app/auth.py:36-41`, `backend/app/routers/media_router.py:122-174`, `backend/app/routers/bot_router.py:18-75` | Secret compromise grants broad API control. |
| HIGH | Provider-controlled title/description values are interpolated into Telegram HTML without escaping. | `bot/handlers/add.py:106-119`, `184-194` | Metadata can alter markup or create misleading content. |
| HIGH | Login has no rate limiting, lockout, or abuse telemetry. | `backend/app/routers/auth_router.py:15-31` | Password guessing is not meaningfully slowed or detected. |
| MEDIUM | CSRF protection is implicit rather than explicit for cookie-authenticated mutations. | `backend/app/routers/auth_router.py:24-31`, `web/src/api.ts:5-19` | Future proxy/frontend changes could expose cross-site state changes. |
| MEDIUM | Screenshot uploads are read fully into memory without size, dimension, or content validation. | `backend/app/routers/resolve_router.py:52-61` | Oversized/malformed uploads can cause resource and AI-cost abuse. |
| MEDIUM | Poster downloads follow redirects and publish content as public JPEG without response limits. | `backend/app/services/storage.py:11-39` | Excessive or unexpected content can be stored and publicly served. |
| MEDIUM | Backend uses MinIO root credentials and public-read objects. | `docker-compose.yml:20-33`, `backend/app/services/storage.py:35-39` | Credential compromise exposes all object data. |
| MEDIUM | JWT secret defaults to `change-me`; production permits plain-text passwords. | `backend/app/config.py:28-33`, `.env.example:14-20` | Misconfiguration can enable token forgery or password disclosure. |
| LOW | Raw provider/API response text is surfaced in bot/frontend errors. | `bot/handlers/add.py:295-301`, `web/src/api.ts:17-20` | Inconsistent information disclosure and poor user messaging. |
| LOW | Security headers, request-size limits, and rate limits are absent at the edge. | `Caddyfile:1-25`, `web/nginx.conf:1-32` | Defense-in-depth is incomplete. |

## Audit conclusion

This is a viable personal-catalog MVP with a sensible modular-monolith foundation, but it is **not ready for unreviewed public production exposure**. The highest-risk issue is authorization design: one bot secret is treated as a universal trusted identity. Input limits, login abuse controls, credential hardening, and object-storage isolation are the next priorities. The UI is functional but needs accessibility and theme-consistency work.

## Proposed action plan for human approval

| Phase | Work | Exit criteria |
|---|---|---|
| 0 — baseline | Confirm threat model, deployment exposure, privilege model, data retention, and run secret/dependency scans. | Approved scope and baseline report. |
| 1 — contain | Split bot/web principals, escape Telegram output, add login throttling and security headers, validate uploads, enforce strong settings, and scope storage credentials. | Negative tests prove bot credentials cannot perform web-only/admin actions; abuse inputs are bounded. |
| 2 — stabilize | Extract application services, add DB invariants/idempotency, shared clients with timeouts, readiness checks, and deployment-owned migrations. | Tests cover vendor failures, duplicate confirmation, rollback, and readiness. |
| 3 — improve UX | Add accessible themed dialogs/controls, shared error states, retries/resets, and generated API types. | Keyboard, screen-reader, contrast, and mobile smoke tests pass. |
| 4 — operate | Add structured audit logs, metrics, backups/restore drills, staged deployment, and rollback documentation. | Alerts, restore, and rollback are tested. |

Implementation should begin only after human approval of Phase 0 assumptions and the privilege model.
