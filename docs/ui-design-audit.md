# UI Design and UX Audit

## Strengths

The primary journey is clear: login, browse/filter, inspect, edit, or add (`web/src/App.tsx:17-59`, `web/src/pages/Catalog.tsx:36-163`). Debounced search, pagination, grid/list modes, lazy poster images, and persisted theme/view preferences are useful for a personal catalog.

## Findings

| Priority | Finding | Evidence | User impact |
|---|---|---|---|
| P1 | Add/edit dialogs hard-code white and gray styling instead of theme tokens. | `web/src/components/AddMediaModal.tsx:81-84`, `web/src/components/EditMediaModal.tsx:72-75`, tokens in `web/src/index.css:5-62` | Dark and custom themes produce poor contrast and visual inconsistency. |
| P1 | Dialogs lack `role="dialog"`, `aria-modal`, focus trapping, and focus restoration. | `web/src/components/MediaDetailModal.tsx:22-35`, add/edit modal roots | Keyboard and screen-reader users can lose context. |
| P1 | Media cards are clickable `div`s rather than keyboard-operable controls. | `web/src/components/MediaCard.tsx:39-45`, `78-84` | Catalog discovery is inaccessible by keyboard. |
| P2 | Icon-only grid/list and status controls rely on glyphs or `title` attributes. | `web/src/components/FilterBar.tsx:71-87`, `web/src/components/MediaCard.tsx:62-68` | Controls have ambiguous accessible names. |
| P2 | Several async failures are silently ignored. | `web/src/components/FilterBar.tsx:52-54`, `web/src/pages/Catalog.tsx:79-80` | Empty or stale UI can look like valid data. |
| P2 | Error strings expose raw exception/API text. | `web/src/pages/Catalog.tsx:65`, `web/src/components/AddMediaModal.tsx:52` | Messages are confusing and may reveal implementation details. |
| P3 | There is no visible result count, clear-filters action, or retry empty state. | `web/src/pages/Catalog.tsx:103-105`, `web/src/components/FilterBar.tsx:58-68` | Users cannot quickly recover from complex filters or transient failures. |

## Recommended design system work

Extract shared `Dialog`, `Button`, `FormField`, and API-error components. Require theme-token-only surfaces and shared focus-ring styles. Add keyboard-operable card semantics, labelled icon controls, focus management, actionable retry states, and a result toolbar with count/reset.

## Acceptance criteria

- All catalog actions work with keyboard only and show visible focus.
- Dialog focus is trapped while open and restored to its trigger.
- All five themes pass contrast checks for dialogs, controls, badges, and disabled states.
- Search, genre loading, save, delete, and status failures show recovery guidance.
- Mobile layouts do not require horizontal scrolling.

