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

  useEffect(() => {
    api.genres.list().then((r) => setGenres(r.genres)).catch(() => {});
  }, []);

  function set(key: keyof Filters, value: string) {
    onChange({ ...filters, [key]: value });
  }

  const selectClass = "border border-border-theme rounded-md px-3 py-1.5 text-sm bg-surface text-text-base focus:ring-primary focus:border-primary";

  return (
    <div className="flex flex-wrap gap-3 items-center">
      <input
        type="search"
        placeholder="Поиск..."
        value={filters.search}
        onChange={(e) => set("search", e.target.value)}
        className={`${selectClass} w-48`}
      />
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
  );
}
