# Refactoring Audit

## Backend

### Findings

| Priority | Finding | Refactoring proposal |
|---|---|---|
| P1 | `confirm` mixes transport, provider calls, storage, domain mapping, and persistence. | Extract a typed `MediaIngestionService`; keep the router as transport glue. |
| P1 | Browser JWT and bot shared-secret authentication are combined in one dependency. | Introduce separate principal types and `require_web_user` / `require_bot_principal` dependencies. |
| P1 | Schemas accept unbounded text, URLs, dictionaries, lists, and upload bytes. | Add field limits, provider URL validation, upload limits, and domain validators. |
| P1 | Enum values and labels are duplicated in Python, TypeScript, and bot dictionaries. | Generate API types from OpenAPI and keep labels in presentation layers. |
| P2 | Storage catches every bucket-creation exception. | Catch only known “already exists” errors; log and map other failures explicitly. |
| P2 | HTTP clients are repeatedly created and have inconsistent timeout behavior. | Manage shared clients in application lifespan and add bounded retry helpers. |
| P2 | `added_by` is client-provided on confirmation. | Derive actor identity from the authenticated principal. |

### Strengths to preserve

The service modules for TMDB, OpenAI, and storage are good seams for dependency injection and testing (`backend/app/services/*`). Typed mappings and response models should remain the public contract while internals are extracted.

## Frontend

### Findings

| Priority | Finding | Refactoring proposal |
|---|---|---|
| P1 | Add/edit/detail modals duplicate shell, errors, actions, and styling. | Extract shared dialog, media form fields, and modal action primitives. |
| P1 | Call sites use string casts for domain values. | Use generated discriminated unions and typed filter builders. |
| P2 | Loading is hand-rolled without cancellation or stale-response protection. | Add `AbortController` and request-key handling; consider a query library only after ownership is defined. |
| P2 | Errors are plain strings and often ignored. | Introduce typed UI error state and consistent retry/notification behavior. |
| P2 | Theme and view preference storage is repeated and silently ignored. | Centralize validated preference storage. |
| P3 | Labels, colors, and enum metadata are repeated across components. | Create shared catalog metadata maps with accessible labels. |

## Safe sequence

1. Establish generated contracts, validation limits, actor derivation, and a stable API error shape.
2. Extract backend services and shared clients without changing endpoints.
3. Extract frontend primitives and theme tokens without changing the user journey.
4. Add regression tests around new seams, then remove duplication.

Preserve endpoint paths and response shapes during the first phase, and keep schema migrations separate from code-only refactors.

