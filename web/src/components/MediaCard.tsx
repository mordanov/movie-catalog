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
  watching:    { emoji: "▶️", label: "Смотрим",    color: "bg-blue-100 text-blue-700" },
  watched:     { emoji: "✅", label: "Просмотрено", color: "bg-green-100 text-green-700" },
};

const STATUS_CYCLE: Record<string, string> = {
  not_watched: "watching",
  watching: "watched",
  watched: "not_watched",
};

interface Props {
  media: Media;
  onDetail?: (media: Media) => void;
  onEdit?: (media: Media) => void;
  onStatusToggle?: (media: Media, nextStatus: string) => void;
  viewMode?: "grid" | "list";
}

export default function MediaCard({ media, onDetail, onEdit, onStatusToggle, viewMode = "grid" }: Props) {
  const title = media.title_ru || media.title;
  const status = STATUS_CONFIG[media.watched_status] ?? STATUS_CONFIG.not_watched;
  const catLabel = CATEGORY_LABELS[media.category] ?? media.category;

  if (viewMode === "list") {
    return (
      <div
        className="bg-surface rounded-lg shadow flex items-center gap-3 px-3 py-2 cursor-pointer hover:ring-1 hover:ring-primary"
        onClick={() => onDetail?.(media)}
      >
        {media.poster_url ? (
          <img src={media.poster_url} alt={title} className="w-10 h-14 object-cover rounded flex-shrink-0" loading="lazy" />
        ) : (
          <div className="w-10 h-14 bg-border-theme rounded flex items-center justify-center text-xl flex-shrink-0">🎬</div>
        )}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-text-base text-sm truncate">{title}</p>
          <p className="text-xs text-muted">{media.year ?? "—"} · {catLabel}</p>
          {media.actors.length > 0 && (
            <p className="text-xs text-muted truncate">{media.actors.slice(0, 3).join(", ")}</p>
          )}
        </div>
        {media.rating_external != null && (
          <span className="text-xs text-muted flex-shrink-0">★ {media.rating_external.toFixed(1)}</span>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onStatusToggle?.(media, STATUS_CYCLE[media.watched_status]); }}
          className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${status.color}`}
          title="Сменить статус"
        >
          {status.emoji}
        </button>
      </div>
    );
  }

  return (
    <div
      className="bg-surface rounded-lg shadow overflow-hidden flex flex-col cursor-pointer hover:ring-1 hover:ring-primary"
      onClick={() => onDetail?.(media)}
    >
      {media.poster_url ? (
        <img src={media.poster_url} alt={title} className="w-full h-48 object-cover" loading="lazy" />
      ) : (
        <div className="w-full h-48 bg-border-theme flex items-center justify-center text-muted text-4xl">🎬</div>
      )}
      <div className="p-3 flex flex-col gap-1 flex-1">
        <h3 className="font-semibold text-text-base text-sm leading-tight line-clamp-2">{title}</h3>
        <p className="text-xs text-muted">{media.year ?? "—"}</p>
        {media.rating_external != null && (
          <p className="text-xs text-muted">★ {media.rating_external.toFixed(1)}</p>
        )}
        <div className="flex flex-wrap gap-1 mt-auto pt-2">
          <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">{catLabel}</span>
          <button
            onClick={(e) => { e.stopPropagation(); onStatusToggle?.(media, STATUS_CYCLE[media.watched_status]); }}
            className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}
            title="Сменить статус"
          >
            {status.emoji} {status.label}
          </button>
        </div>
        {media.trailer_url && (
          <a
            href={media.trailer_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="mt-1 text-xs text-primary hover:text-primary-hover"
          >
            ▶ Трейлер
          </a>
        )}
        {onEdit && (
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(media); }}
            className="mt-1 text-xs text-primary hover:text-primary-hover text-left"
          >
            Редактировать
          </button>
        )}
      </div>
    </div>
  );
}
