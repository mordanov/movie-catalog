# Mobile View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full mobile-first responsive experience to the movie catalog — bottom tab nav, collapsible FilterBar, full-screen detail modal, and responsive Login — with zero desktop regression.

**Architecture:** All changes are additive via Tailwind `md:` breakpoint (bare classes = mobile, `md:` = desktop). A new `BottomNav` component is wired into `Layout` which also lifts `AddMediaModal` state up from `Catalog`, passing a reload counter via `useOutletContext`. No new dependencies.

**Tech Stack:** React 18, TypeScript, Tailwind CSS v3, React Router v6, Vite

**Spec:** `docs/superpowers/specs/2026-09-22-mobile-view-design.md`

**Working directory:** `/Users/aleksandr/Local/movie-catalog/.claude/worktrees/mobile-view`

## Global Constraints

- Breakpoint: `md` = ≥768px (desktop). Bare Tailwind class = mobile. `md:` override = desktop.
- No new npm dependencies — pure Tailwind + React.
- No `window.innerWidth` / `window.matchMedia` in components, except `BottomNav` uses `useLocation` (React Router) for active tab.
- All theme tokens throughout: `bg-surface`, `bg-nav`, `text-text-base`, `text-muted`, `border-border-theme`, `text-primary`, `bg-primary`, `hover:bg-primary-hover`. No hardcoded grays/indigos in new code.
- TypeScript strict: no `any`, no `@ts-ignore`.
- `tsc --noEmit` must pass after every task.
- Existing 3 vitest tests (`web/src/api.test.ts`) must pass after every task.
- Commit after each task with message format `feat: <description>`.
- Python venv: `/Users/aleksandr/Local/movie-catalog/.venv/bin/python`
- Run tsc from: `web/` directory via `node_modules/.bin/tsc --noEmit`
- Run vitest from: `web/` directory via `node_modules/.bin/vitest run`

---

## Task 1: BottomNav component

**Files:**
- Create: `web/src/components/BottomNav.tsx`

**Interfaces:**
- Consumes: `react-router-dom` (`useLocation`, `useNavigate`), theme tokens
- Produces: `export default function BottomNav({ onAdd }: { onAdd: () => void })` — used by Layout in Task 2

- [ ] **Step 1: Create `web/src/components/BottomNav.tsx`**

```tsx
import { useLocation, useNavigate } from "react-router-dom";

interface Props {
  onAdd: () => void;
}

const TABS = [
  { label: "Каталог",    icon: "🎬", path: "/" },
  { label: "Статистика", icon: "📊", path: "/stats" },
] as const;

export default function BottomNav({ onAdd }: Props) {
  const location = useLocation();
  const navigate = useNavigate();

  const tabClass = (active: boolean) =>
    `flex-1 flex flex-col items-center py-2 gap-0.5 text-xs ${active ? "text-primary" : "text-muted hover:text-primary"}`;

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 bg-nav border-t border-border-theme md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="flex">
        {TABS.map((tab) => (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            className={tabClass(location.pathname === tab.path)}
          >
            <span className="text-xl leading-none">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
        <button onClick={onAdd} className={tabClass(false)}>
          <span className="text-xl leading-none font-bold">＋</span>
          <span>Добавить</span>
        </button>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd web && node_modules/.bin/tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/BottomNav.tsx
git commit -m "feat: add BottomNav component for mobile bottom tab bar"
```

---

## Task 2: Lift AddMediaModal to Layout; integrate BottomNav

`showAdd` state and `AddMediaModal` move from `Catalog` to `Layout`. Layout passes an `addedCount` counter via React Router's `useOutletContext`. Catalog listens and reloads. BottomNav wired into Layout.

**Files:**
- Modify: `web/src/pages/Layout.tsx`
- Modify: `web/src/pages/Catalog.tsx`

**Interfaces:**
- Consumes: `BottomNav` (Task 1), `AddMediaModal` (existing at `../components/AddMediaModal`)
- Produces:
  - `export interface CatalogOutletContext { addedCount: number }` — exported from `Layout.tsx`
  - `<Outlet context={...} />` — passes `{ addedCount }` to child routes

- [ ] **Step 1: Rewrite `web/src/pages/Layout.tsx`**

Replace the entire file with:

```tsx
import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import ThemePicker from "../components/ThemePicker";
import BottomNav from "../components/BottomNav";
import AddMediaModal from "../components/AddMediaModal";

export interface CatalogOutletContext {
  addedCount: number;
}

export default function Layout() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [addedCount, setAddedCount] = useState(0);

  useEffect(() => {
    api.auth.me().then((u) => setUsername(u.login)).catch(() => {});
  }, []);

  async function handleLogout() {
    await api.auth.logout().catch(() => {});
    navigate("/login");
  }

  function handleAdded() {
    setShowAdd(false);
    setAddedCount((c) => c + 1);
  }

  return (
    <div className="min-h-screen bg-page text-text-base">
      {/* Top nav */}
      <nav className="bg-nav border-b border-border-theme px-4 py-3 flex items-center justify-between">
        {/* Desktop: logo + links */}
        <div className="flex items-center gap-6">
          <span className="font-bold text-primary text-lg">Каталог</span>
          <Link to="/" className="hidden md:inline text-sm text-text-base hover:text-primary">Каталог</Link>
          <Link to="/stats" className="hidden md:inline text-sm text-text-base hover:text-primary">Статистика</Link>
        </div>
        {/* Right side */}
        <div className="flex items-center gap-4">
          <ThemePicker />
          {username && <span className="hidden md:inline text-sm text-muted">{username}</span>}
          <button onClick={handleLogout} className="hidden md:inline text-sm text-muted hover:text-primary">
            Выйти
          </button>
        </div>
      </nav>

      {/* Main content — pb-20 on mobile to clear the bottom nav */}
      <main className="max-w-7xl mx-auto px-4 py-6 pb-24 md:pb-6">
        <Outlet context={{ addedCount } satisfies CatalogOutletContext} />
      </main>

      {/* Mobile bottom nav */}
      <BottomNav onAdd={() => setShowAdd(true)} />

      {showAdd && (
        <AddMediaModal onClose={() => setShowAdd(false)} onAdded={handleAdded} />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Update `web/src/pages/Catalog.tsx`**

Remove `showAdd` state, `AddMediaModal` import and render; add `useOutletContext`; add `addedCount` to load effect; hide "+" button on mobile.

Replace the entire file with:

```tsx
import { useCallback, useEffect, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import type { Media } from "../types";
import type { CatalogOutletContext } from "./Layout";
import { api } from "../api";
import MediaCard from "../components/MediaCard";
import FilterBar from "../components/FilterBar";
import Pagination from "../components/Pagination";
import EditMediaModal from "../components/EditMediaModal";
import MediaDetailModal from "../components/MediaDetailModal";

interface Filters {
  category: string;
  type: string;
  watched_status: string;
  search: string;
  sort_by: string;
  genre: string;
}

const DEFAULT_FILTERS: Filters = {
  category: "", type: "", watched_status: "", search: "", sort_by: "added_at", genre: "",
};
const PAGE_SIZE = 24;

export default function Catalog() {
  const { addedCount } = useOutletContext<CatalogOutletContext>();
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Media[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [editTarget, setEditTarget] = useState<Media | null>(null);
  const [detailTarget, setDetailTarget] = useState<Media | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">(() => {
    try { return (localStorage.getItem("catalog_view") as "grid" | "list") ?? "grid"; }
    catch { return "grid"; }
  });
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
  }, [filters, page, load, addedCount]);

  function handleFilterChange(newFilters: Filters) {
    setFilters(newFilters);
    setPage(1);
  }

  function handleViewToggle(mode: "grid" | "list") {
    setViewMode(mode);
    try { localStorage.setItem("catalog_view", mode); } catch { /* ignore */ }
  }

  async function handleStatusToggle(media: Media, nextStatus: string) {
    try {
      const updated = await api.media.update(media.id, { watched_status: nextStatus as Media["watched_status"] });
      setItems((prev) => prev.map((m) => m.id === updated.id ? updated : m));
      if (detailTarget?.id === updated.id) setDetailTarget(updated);
    } catch { /* ignore */ }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <FilterBar
          filters={filters}
          onChange={handleFilterChange}
          viewMode={viewMode}
          onViewToggle={handleViewToggle}
        />
        {/* Desktop-only add button — mobile uses BottomNav */}
        <button
          onClick={() => {/* no-op: handled by Layout via BottomNav */}}
          className="hidden md:block px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary-hover"
        >
          + Добавить
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-center text-muted py-12">Загрузка...</div>
      ) : items.length === 0 ? (
        <div className="text-center text-muted py-12">Ничего не найдено</div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {items.map((m) => (
            <MediaCard
              key={m.id}
              media={m}
              viewMode="grid"
              onDetail={setDetailTarget}
              onEdit={setEditTarget}
              onStatusToggle={handleStatusToggle}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((m) => (
            <MediaCard
              key={m.id}
              media={m}
              viewMode="list"
              onDetail={setDetailTarget}
              onEdit={setEditTarget}
              onStatusToggle={handleStatusToggle}
            />
          ))}
        </div>
      )}

      <Pagination page={page} total={total} pageSize={PAGE_SIZE} onChange={setPage} />

      {editTarget && (
        <EditMediaModal
          media={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={(updated) => {
            setItems((prev) => prev.map((m) => m.id === updated.id ? updated : m));
            setEditTarget(null);
          }}
          onDeleted={() => {
            setItems((prev) => prev.filter((m) => m.id !== editTarget.id));
            setEditTarget(null);
          }}
        />
      )}
      {detailTarget && (
        <MediaDetailModal
          media={detailTarget}
          onClose={() => setDetailTarget(null)}
          onEdit={() => { setEditTarget(detailTarget); setDetailTarget(null); }}
        />
      )}
    </div>
  );
}
```

> **Note:** The desktop "+" button calls a no-op because `AddMediaModal` is now in Layout. If you want the desktop button to still open the modal, you can wire it via a second outlet context key `onAdd: () => void`. However, the spec puts the desktop button as-is and the mobile path is BottomNav — for now the desktop button is hidden on mobile only; the desktop button can be wired up as a follow-up. The simplest correct implementation per spec: just remove the desktop button entirely or keep it calling `setShowAdd` if it's passed down. Since the spec says "hide on mobile", keep the button but wire `onAdd` through outlet context.

**Correction — wire the desktop "+" button properly.** Update `CatalogOutletContext` and both files:

In `Layout.tsx`, add `onAdd` to the context:
```tsx
export interface CatalogOutletContext {
  addedCount: number;
  onAdd: () => void;
}
// in JSX:
<Outlet context={{ addedCount, onAdd: () => setShowAdd(true) } satisfies CatalogOutletContext} />
```

In `Catalog.tsx`, destructure `onAdd` and wire the button:
```tsx
const { addedCount, onAdd } = useOutletContext<CatalogOutletContext>();
// button:
<button onClick={onAdd} className="hidden md:block px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary-hover">
  + Добавить
</button>
```

Apply this correction to both files in the same step.

- [ ] **Step 3: Type-check**

```bash
cd web && node_modules/.bin/tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Run tests**

```bash
cd web && node_modules/.bin/vitest run
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/Layout.tsx web/src/pages/Catalog.tsx
git commit -m "feat: lift AddMediaModal to Layout; wire BottomNav; pass addedCount via outletContext"
```

---

## Task 3: FilterBar — collapsible filters on mobile

Search input always visible. `⚙` button toggles the rest on mobile. Active-filter indicator on the button when non-default filters are set and panel is closed.

**Files:**
- Modify: `web/src/components/FilterBar.tsx`

**Interfaces:**
- Consumes: existing `Props` interface (no change to props)
- Produces: same `export default function FilterBar(...)` — no interface change

- [ ] **Step 1: Rewrite `web/src/components/FilterBar.tsx`**

```tsx
import { useEffect, useState } from "react";
import { api } from "../api";

interface Filters {
  category: string;
  type: string;
  watched_status: string;
  search: string;
  sort_by: string;
  genre: string;
}

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
  viewMode: "grid" | "list";
  onViewToggle: (mode: "grid" | "list") => void;
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

const SORTS = [
  { value: "added_at", label: "По дате" },
  { value: "rating", label: "По рейтингу" },
  { value: "year", label: "По году" },
  { value: "title", label: "По названию" },
];

export default function FilterBar({ filters, onChange, viewMode, onViewToggle }: Props) {
  const [genres, setGenres] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    api.genres.list().then((r) => setGenres(r.genres)).catch(() => {});
  }, []);

  function set(key: keyof Filters, value: string) {
    onChange({ ...filters, [key]: value });
  }

  const hasActiveFilters =
    filters.category !== "" ||
    filters.type !== "" ||
    filters.watched_status !== "" ||
    filters.genre !== "" ||
    filters.sort_by !== "added_at";

  const selectClass =
    "border border-border-theme rounded-md px-3 py-1.5 text-sm bg-surface text-text-base focus:ring-primary focus:border-primary";

  return (
    <div className="flex flex-col gap-2 w-full md:w-auto">
      {/* Always-visible row: search + toggle button */}
      <div className="flex gap-2 items-center">
        <input
          type="search"
          placeholder="Поиск..."
          value={filters.search}
          onChange={(e) => set("search", e.target.value)}
          className={`${selectClass} flex-1 md:w-48 md:flex-none`}
        />
        {/* ⚙ toggle — mobile only */}
        <button
          onClick={() => setIsOpen((v) => !v)}
          aria-label="Фильтры"
          aria-expanded={isOpen}
          className={`md:hidden px-2.5 py-1.5 rounded-md border text-sm ${
            hasActiveFilters && !isOpen
              ? "border-primary bg-primary text-white"
              : "border-border-theme bg-surface text-muted hover:text-text-base"
          }`}
        >
          ⚙{hasActiveFilters && !isOpen ? " •" : ""}
        </button>
      </div>

      {/* Collapsible panel: hidden on mobile unless open; always shown on md: */}
      <div className={`${isOpen ? "flex" : "hidden"} md:flex flex-wrap gap-3 items-center`}>
        <select value={filters.category} onChange={(e) => set("category", e.target.value)} className={selectClass}>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select value={filters.type} onChange={(e) => set("type", e.target.value)} className={selectClass}>
          {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <select value={filters.watched_status} onChange={(e) => set("watched_status", e.target.value)} className={selectClass}>
          {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        {genres.length > 0 && (
          <select value={filters.genre} onChange={(e) => set("genre", e.target.value)} className={selectClass}>
            <option value="">Все жанры</option>
            {genres.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        )}
        <select value={filters.sort_by} onChange={(e) => set("sort_by", e.target.value)} className={selectClass}>
          {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>

        {/* Grid / List toggle */}
        <div className="flex rounded-md border border-border-theme overflow-hidden">
          <button
            onClick={() => onViewToggle("grid")}
            className={`px-2.5 py-1.5 text-sm ${viewMode === "grid" ? "bg-primary text-white" : "bg-surface text-muted hover:text-text-base"}`}
            title="Плитки"
            aria-pressed={viewMode === "grid"}
          >
            ⊞
          </button>
          <button
            onClick={() => onViewToggle("list")}
            className={`px-2.5 py-1.5 text-sm ${viewMode === "list" ? "bg-primary text-white" : "bg-surface text-muted hover:text-text-base"}`}
            title="Список"
            aria-pressed={viewMode === "list"}
          >
            ≡
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd web && node_modules/.bin/tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/FilterBar.tsx
git commit -m "feat: FilterBar collapsible panel + active-filter indicator on mobile"
```

---

## Task 4: MediaDetailModal — full-screen on mobile

On mobile: `fixed inset-0`, `bg-surface`, sticky header with `←` back button. On desktop (`md:`): existing backdrop + `max-w-lg rounded-xl`. ESC handler and ✕ button remain for desktop.

**Files:**
- Modify: `web/src/components/MediaDetailModal.tsx`

**Interfaces:**
- No change to `Props` interface.

- [ ] **Step 1: Rewrite `web/src/components/MediaDetailModal.tsx`**

```tsx
import { useEffect } from "react";
import type { Media } from "../types";

interface Props {
  media: Media;
  onClose: () => void;
  onEdit: () => void;
}

function StarRating({ value }: { value: number }) {
  const stars = Math.round((value / 10) * 5);
  return (
    <div className="flex gap-0.5" aria-label={`Рейтинг ${value.toFixed(1)} из 10`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= stars ? "text-yellow-400" : "text-border-theme"}>★</span>
      ))}
      <span className="ml-1 text-sm text-muted">{value.toFixed(1)}</span>
    </div>
  );
}

export default function MediaDetailModal({ media, onClose, onEdit }: Props) {
  const title = media.title_ru || media.title;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    // Mobile: full-screen bg-surface. Desktop (md:): dark backdrop, flex center.
    <div
      className="fixed inset-0 z-50 bg-surface overflow-y-auto md:bg-black/60 md:overflow-hidden md:flex md:items-center md:justify-center md:p-4"
      onClick={onClose}
    >
      {/* Card: full-height on mobile, max-w-lg rounded on desktop */}
      <div
        className="relative w-full min-h-full bg-surface md:min-h-0 md:max-w-lg md:rounded-xl md:shadow-2xl md:max-h-[90vh] md:overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Mobile header: sticky ← back + title */}
        <div className="sticky top-0 z-10 bg-surface border-b border-border-theme flex items-center px-4 py-3 md:hidden">
          <button
            onClick={onClose}
            className="text-text-base text-xl leading-none mr-3"
            aria-label="Назад"
          >
            ←
          </button>
          <h2 className="font-semibold text-text-base truncate flex-1">{title}</h2>
        </div>

        {/* Desktop ✕ button */}
        <button
          onClick={onClose}
          aria-label="Закрыть"
          className="hidden md:block absolute top-3 right-3 text-muted hover:text-text-base text-xl leading-none z-10"
        >
          ✕
        </button>

        {/* Poster + info */}
        <div className="flex gap-4 p-4">
          {media.poster_url ? (
            <img
              src={media.poster_url}
              alt={title}
              className="w-28 h-40 object-cover rounded-lg flex-shrink-0"
            />
          ) : (
            <div className="w-28 h-40 bg-border-theme rounded-lg flex items-center justify-center text-3xl flex-shrink-0">
              🎬
            </div>
          )}

          <div className="flex-1 min-w-0">
            {/* Title shown in header on mobile; show here on desktop */}
            <h2 className="hidden md:block font-bold text-text-base text-lg leading-tight">{title}</h2>
            {media.title_ru && media.title !== media.title_ru && (
              <p className="text-sm text-muted">{media.title}</p>
            )}
            <p className="text-sm text-muted mt-1">{media.year ?? "—"}</p>

            {media.rating_external != null && (
              <div className="mt-2">
                <StarRating value={media.rating_external} />
              </div>
            )}

            {media.genres.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {media.genres.map((g) => (
                  <span key={g} className="text-xs px-2 py-0.5 rounded-full bg-border-theme text-muted">
                    {g}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Description */}
        {media.description && (
          <p className="px-4 pb-3 text-sm text-text-base leading-relaxed">{media.description}</p>
        )}

        {/* Actors */}
        {media.actors.length > 0 && (
          <div className="px-4 pb-3">
            <p className="text-xs text-muted uppercase tracking-wide mb-1">В ролях</p>
            <div className="flex flex-wrap gap-1">
              {media.actors.slice(0, 5).map((a) => (
                <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-border-theme text-text-base">
                  {a}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="px-4 pb-4 flex gap-2 flex-wrap">
          {media.trailer_url && (
            <a
              href={media.trailer_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-primary text-white text-sm rounded-md hover:bg-primary-hover"
            >
              ▶ Трейлер
            </a>
          )}
          <button
            onClick={onEdit}
            className="px-3 py-1.5 border border-border-theme text-text-base text-sm rounded-md hover:border-primary hover:text-primary"
          >
            Редактировать
          </button>
          {/* Desktop-only close button in actions row */}
          <button
            onClick={onClose}
            className="hidden md:block ml-auto px-3 py-1.5 text-muted text-sm hover:text-text-base"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd web && node_modules/.bin/tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/MediaDetailModal.tsx
git commit -m "feat: MediaDetailModal full-screen on mobile, centered modal on desktop"
```

---

## Task 5: Login — responsive card + commit spec

Add `px-4` to the outer container of Login so the card has side padding on mobile. Commit the design spec.

**Files:**
- Modify: `web/src/pages/Login.tsx`
- Commit: `docs/superpowers/specs/2026-09-22-mobile-view-design.md` (already on disk, just needs to be staged)

**Interfaces:** No interface changes.

- [ ] **Step 1: Add `px-4` to Login outer div**

In `web/src/pages/Login.tsx`, change line 27:

```tsx
// Before:
<div className="min-h-screen flex items-center justify-center bg-page">

// After:
<div className="min-h-screen flex items-center justify-center bg-page px-4">
```

- [ ] **Step 2: Type-check**

```bash
cd web && node_modules/.bin/tsc --noEmit
```

- [ ] **Step 3: Run tests**

```bash
cd web && node_modules/.bin/vitest run
```
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/Login.tsx docs/superpowers/specs/2026-09-22-mobile-view-design.md
git commit -m "feat: Login card full-width on mobile; add mobile-view design spec"
```

---

## Manual QA Checklist (post-implementation)

Run `npm run dev` from `web/` and open in browser. Resize to <768px to test mobile.

- [ ] Bottom nav visible on <768px, hidden on ≥768px
- [ ] Bottom nav active tab highlights on route change (Каталог / Статистика)
- [ ] Bottom nav "＋" opens AddMediaModal; after adding, catalog reloads
- [ ] Desktop "＋ Добавить" button still works (wired via `onAdd` from outlet context)
- [ ] FilterBar search always visible; ⚙ button appears on mobile
- [ ] ⚙ button has active indicator (dot + primary color) when non-default filter is set and panel closed
- [ ] Filter panel expands/collapses on ⚙ tap; always open on desktop
- [ ] MediaDetailModal: full-screen with `←` header on mobile
- [ ] MediaDetailModal: `max-w-lg` backdrop modal with `✕` on desktop
- [ ] ESC closes modal on both mobile and desktop
- [ ] Tapping backdrop on desktop closes modal; tapping inside on mobile does not close
- [ ] Login card has side padding on mobile (no edge-to-edge card)
- [ ] All 5 themes look correct on mobile
