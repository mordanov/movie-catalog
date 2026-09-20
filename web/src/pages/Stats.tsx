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
    api.stats.get()
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
