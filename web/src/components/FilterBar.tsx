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
