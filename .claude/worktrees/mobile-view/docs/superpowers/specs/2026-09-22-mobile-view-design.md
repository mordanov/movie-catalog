# Mobile View Design Spec
Date: 2026-09-22  
Branch: `worktree-mobile-view` (based on `worktree-ui-enhancements`)

## Goal

Add a full mobile-first responsive experience to the movie catalog web app. Desktop behaviour is unchanged. All changes are additive via Tailwind `md:` breakpoint (≥768px = desktop).

---

## Breakpoint Convention

| Token | Value | Meaning |
|-------|-------|---------|
| `md:` | ≥768px | Desktop styles |
| (bare) | <768px | Mobile styles |

All new responsive classes follow mobile-first order: bare class = mobile, `md:` override = desktop.

---

## 1. Navigation

### Desktop (unchanged)
Top nav bar with logo, links (Каталог / Статистика), ThemePicker, username, logout button.

### Mobile
**Top bar** — simplified: logo left, ThemePicker right. Links and user info removed from top bar.

**Bottom tab bar** — `fixed bottom-0 left-0 right-0`, `bg-nav border-t border-border-theme`, hidden on `md:`.  
Safe-area padding: `pb-[env(safe-area-inset-bottom)]` for iPhone notch.

Three tabs, equal width (`flex-1`), each `flex flex-col items-center py-2 gap-0.5`:

| Tab | Icon | Label | Action |
|-----|------|-------|--------|
| Каталог | 🎬 | Каталог | `navigate("/")` |
| Статистика | 📊 | Статистика | `navigate("/stats")` |
| Добавить | ＋ | Добавить | opens AddMediaModal |

Active tab highlighted with `text-primary`; inactive `text-muted`.

### State lifting: AddMediaModal

`showAdd` state and `AddMediaModal` rendering move from `Catalog.tsx` up to `Layout.tsx`.  
`Layout` passes `{ addedCount }` via React Router `useOutletContext`.  
`Catalog` watches `addedCount` with a `useEffect` to trigger a reload.  
The existing "＋ Добавить" button in `Catalog` is hidden on mobile (`hidden md:block`), since the bottom nav provides this action.

### Main content area
`<main>` gets `pb-20 md:pb-0` to prevent content being obscured by the bottom nav.

### New file
`web/src/components/BottomNav.tsx`

---

## 2. FilterBar

### Desktop (unchanged)
All controls inline in one `flex-wrap` row.

### Mobile
**Always visible row:** `[🔍 Поиск...]` input (flex-1) + `[⚙]` toggle button.  
**Collapsible panel:** the remaining 5 selects (category, type, status, genre, sort_by) + grid/list toggle, revealed below the search row when ⚙ is active.

#### Behaviour
- `isOpen` local state, default `false`.  
- ⚙ button shows active indicator (`bg-primary text-white`) when any non-default filter is set AND the panel is closed.  
- On `md:`, panel is always expanded, ⚙ button hidden.  
- Collapsible div: `hidden md:block` when closed, `block` when open.

---

## 3. MediaDetailModal

### Desktop (unchanged)
Backdrop `bg-black/60`, centered `max-w-lg rounded-xl`, ✕ button top-right, ESC closes.

### Mobile
Full-screen overlay: `fixed inset-0 z-50 bg-surface overflow-y-auto`.  
No backdrop, no rounded corners, no max-width constraint.

**Mobile header bar** (`sticky top-0 bg-surface border-b border-border-theme`):
- `←` back button left → `onClose()`  
- Title (truncated) centre  
- ✕ button hidden on mobile (redundant)

Implementation via Tailwind classes only:
```
Outer:        fixed inset-0 z-50 bg-surface overflow-y-auto
              md:bg-black/60 md:flex md:items-center md:justify-center md:p-4
Inner card:   w-full min-h-full relative
              md:min-h-0 md:max-w-lg md:rounded-xl md:shadow-2xl md:max-h-[90vh] md:overflow-y-auto
Mobile hdr:   ... md:hidden
Desktop ✕:    ... hidden md:block
```
ESC keydown handler active on both.

---

## 4. Login page

Add `w-full sm:max-w-md sm:mx-auto` to the card for full-width on mobile.

---

## Component / File Change Summary

| File | Type | Change |
|------|------|--------|
| `web/src/components/BottomNav.tsx` | **new** | Mobile bottom tab bar |
| `web/src/pages/Layout.tsx` | modify | Simplified mobile top bar; render BottomNav; lift showAdd + AddMediaModal; pass addedCount via outletContext |
| `web/src/components/FilterBar.tsx` | modify | isOpen toggle; ⚙ button; collapsible panel on mobile |
| `web/src/components/MediaDetailModal.tsx` | modify | Full-screen mobile layout; mobile header with ← back |
| `web/src/pages/Catalog.tsx` | modify | Remove showAdd state; consume outletContext addedCount; hide "+ Добавить" button on mobile |
| `web/src/pages/Login.tsx` | modify | Full-width card on mobile |

---

## Constraints

- No new dependencies (pure Tailwind + React).
- No JS `window.innerWidth` — responsive via CSS classes only, except `BottomNav` active tab detection (uses `useLocation`).
- ESC close on MediaDetailModal remains for both mobile and desktop.
- All theme tokens (`bg-surface`, `text-text-base`, etc.) throughout — no hardcoded colors.
- TypeScript strict — no `any`, no `@ts-ignore`.

---

## Testing

- `tsc --noEmit` must pass.
- Existing 3 frontend tests must pass.
- Manual checklist:
  - [ ] Bottom nav visible on viewport <768px, hidden on ≥768px
  - [ ] Bottom nav "＋" opens AddMediaModal; new item appears in Catalog
  - [ ] Active tab highlighted correctly on route change
  - [ ] FilterBar ⚙ toggle shows/hides filter panel on mobile
  - [ ] Active-filter indicator on ⚙ when non-default filter is active and panel closed
  - [ ] MediaDetailModal: full-screen with ← on mobile; max-w-lg modal on desktop
  - [ ] ESC closes modal on both
  - [ ] Login card full-width on mobile
  - [ ] No visual regression on desktop
