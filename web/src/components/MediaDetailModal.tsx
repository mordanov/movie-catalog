import type { Media } from "../types";

interface Props {
  media: Media;
  onClose: () => void;
  onEdit: () => void;
}

function StarRating({ value }: { value: number }) {
  // TMDB rating is 0-10; display as 5 stars
  const stars = Math.round((value / 10) * 5);
  return (
    <div className="flex gap-0.5" aria-label={`Рейтинг ${value.toFixed(1)} из 10`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= stars ? "text-yellow-400" : "text-border-theme"}>
          ★
        </span>
      ))}
      <span className="ml-1 text-sm text-muted">{value.toFixed(1)}</span>
    </div>
  );
}

export default function MediaDetailModal({ media, onClose, onEdit }: Props) {
  const title = media.title_ru || media.title;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
      onClick={onClose}
    >
      <div
        className="bg-surface rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex gap-4 p-4">
          {/* Poster */}
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

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-text-base text-lg leading-tight">{title}</h2>
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
          <button
            onClick={onClose}
            className="ml-auto px-3 py-1.5 text-muted text-sm hover:text-text-base"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}
