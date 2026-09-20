import { FormEvent, useState } from "react";
import type { CartoonSubtype, Media, MediaCategory, WatchedStatus } from "../types";
import { api } from "../api";

interface Props {
  media: Media;
  onClose: () => void;
  onSaved: (updated: Media) => void;
  onDeleted: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  cartoon: "Мультфильм",
  family_movie: "Семейный фильм",
  adult_movie: "Взрослый фильм",
  kids_series: "Детский сериал",
  adult_series: "Взрослый сериал",
};

const SUBTYPE_LABELS: Record<string, string> = {
  disney: "Disney",
  pixar: "Pixar",
  soviet: "Советский",
  russian: "Российский",
  other: "Другой",
};

const STATUS_LABELS: Record<string, string> = {
  not_watched: "Не смотрели",
  watching: "Смотрим",
  watched: "Просмотрено",
};

export default function EditMediaModal({ media, onClose, onSaved, onDeleted }: Props) {
  const [titleRu, setTitleRu] = useState(media.title_ru ?? "");
  const [category, setCategory] = useState<MediaCategory>(media.category);
  const [subtype, setSubtype] = useState<CartoonSubtype | null>(media.cartoon_subtype);
  const [watchedStatus, setWatchedStatus] = useState<WatchedStatus>(media.watched_status);
  const [notes, setNotes] = useState(media.notes ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleDelete() {
    const title = media.title_ru || media.title;
    if (!window.confirm(`Удалить «${title}»?`)) return;
    setLoading(true);
    try {
      await api.media.delete(media.id);
      onDeleted();
      onClose();
    } catch (e) {
      setError(`Ошибка удаления: ${e}`);
      setLoading(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const updated = await api.media.update(media.id, {
        title_ru: titleRu || undefined,
        category,
        cartoon_subtype: category === "cartoon" ? subtype : null,
        watched_status: watchedStatus,
        notes: notes || undefined,
      });
      onSaved(updated);
      onClose();
    } catch (e) {
      setError(`Ошибка: ${e}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Редактировать</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">{error}</div>
          )}

          <div>
            <p className="text-xs text-gray-400 mb-1">Оригинальное название</p>
            <p className="font-medium text-sm">{media.title} {media.year ? `(${media.year})` : ""}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Русское название</label>
            <input
              type="text"
              value={titleRu}
              onChange={(e) => setTitleRu(e.target.value)}
              placeholder={media.title}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Категория</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as MediaCategory)}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            >
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          {category === "cartoon" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Тип мультфильма</label>
              <select
                value={subtype ?? ""}
                onChange={(e) => setSubtype((e.target.value as CartoonSubtype) || null)}
                className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
              >
                <option value="">— Выбрать —</option>
                {Object.entries(SUBTYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Статус просмотра</label>
            <select
              value={watchedStatus}
              onChange={(e) => setWatchedStatus(e.target.value as WatchedStatus)}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            >
              {Object.entries(STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Заметки</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={handleDelete}
              disabled={loading}
              className="py-2 px-3 border border-red-300 text-red-600 rounded-md text-sm hover:bg-red-50 disabled:opacity-50"
            >
              Удалить
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? "Сохранение..." : "Сохранить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
