import type { Media } from "../types";

const CATEGORY_LABELS: Record<string, string> = {
  cartoon: "Мультфильм",
  family_movie: "Семейный фильм",
  adult_movie: "Взрослый фильм",
  kids_series: "Детский сериал",
  adult_series: "Взрослый сериал",
};

const STATUS_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  not_watched: { emoji: "👀", label: "Не смотрели", color: "bg-gray-100 text-gray-600" },
  watching: { emoji: "▶️", label: "Смотрим", color: "bg-blue-100 text-blue-700" },
  watched: { emoji: "✅", label: "Просмотрено", color: "bg-green-100 text-green-700" },
};

interface Props {
  media: Media;
  onEdit?: (media: Media) => void;
}

export default function MediaCard({ media, onEdit }: Props) {
  const title = media.title_ru || media.title;
  const status = STATUS_CONFIG[media.watched_status] ?? STATUS_CONFIG.not_watched;
  const catLabel = CATEGORY_LABELS[media.category] ?? media.category;

  return (
    <div className="bg-surface rounded-lg shadow overflow-hidden flex flex-col">
      {media.poster_url ? (
        <img
          src={media.poster_url}
          alt={title}
          className="w-full h-48 object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-48 bg-border-theme flex items-center justify-center text-muted text-4xl">
          🎬
        </div>
      )}
      <div className="p-3 flex flex-col gap-1 flex-1">
        <h3 className="font-semibold text-text-base text-sm leading-tight line-clamp-2">{title}</h3>
        <p className="text-xs text-muted">{media.year ?? "—"}</p>
        <div className="flex flex-wrap gap-1 mt-auto pt-2">
          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">{catLabel}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}>
            {status.emoji} {status.label}
          </span>
        </div>
        {onEdit && (
          <button
            onClick={() => onEdit(media)}
            className="mt-2 text-xs text-primary hover:text-primary-hover text-left"
          >
            Редактировать
          </button>
        )}
      </div>
    </div>
  );
}
