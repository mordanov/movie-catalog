import { FormEvent, useCallback, useRef, useState } from "react";
import type { Candidate, MediaCategory, CartoonSubtype } from "../types";
import { api } from "../api";

interface Props {
  onClose: () => void;
  onAdded: () => void;
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

type Step = "search" | "candidates" | "confirm";

export default function AddMediaModal({ onClose, onAdded }: Props) {
  const [step, setStep] = useState<Step>("search");
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [category, setCategory] = useState<MediaCategory>("family_movie");
  const [subtype, setSubtype] = useState<CartoonSubtype | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError("");
    try {
      const results = await api.resolve.search(q);
      setCandidates(results);
      setStep("candidates");
    } catch (e) {
      setError(`Ошибка поиска: ${e}`);
    } finally {
      setLoading(false);
    }
  }, []);

  function handleQueryChange(val: string) {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(val), 500);
  }

  function selectCandidate(c: Candidate) {
    setSelected(c);
    setStep("confirm");
  }

  async function handleConfirm(e: FormEvent) {
    e.preventDefault();
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      await api.media.confirm({
        tmdb_id: selected.tmdb_id,
        media_type: selected.media_type,
        category,
        cartoon_subtype: category === "cartoon" ? subtype : null,
        source: "web_ui",
        notes: notes || undefined,
      });
      onAdded();
      onClose();
    } catch (e) {
      setError(`Ошибка: ${e}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Добавить в каталог</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">{error}</div>
          )}

          {step === "search" && (
            <div>
              <input
                type="text"
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                placeholder="Введите название фильма или сериала..."
                autoFocus
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
              {loading && <p className="text-sm text-gray-500 mt-2">Поиск...</p>}
            </div>
          )}

          {step === "candidates" && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-gray-600">
                  {candidates[0]?.disambiguation_question || "Выберите нужный вариант:"}
                </p>
                <button onClick={() => setStep("search")} className="text-xs text-indigo-600">← Назад</button>
              </div>
              <div className="space-y-2">
                {candidates.map((c) => (
                  <button
                    key={`${c.tmdb_id}-${c.media_type}`}
                    onClick={() => selectCandidate(c)}
                    className="w-full text-left flex gap-3 p-2 rounded-lg border border-gray-200 hover:border-indigo-400 hover:bg-indigo-50 transition"
                  >
                    {c.poster_url && (
                      <img src={c.poster_url} alt={c.title} className="w-12 h-16 object-cover rounded" />
                    )}
                    <div>
                      <p className="font-medium text-sm">{c.title}</p>
                      <p className="text-xs text-gray-400">{c.year ?? "—"}</p>
                      <p className="text-xs text-gray-500 line-clamp-2">{c.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === "confirm" && selected && (
            <form onSubmit={handleConfirm} className="space-y-4">
              <div className="flex gap-3">
                {selected.poster_url && (
                  <img src={selected.poster_url} alt={selected.title} className="w-16 h-24 object-cover rounded" />
                )}
                <div>
                  <p className="font-semibold">{selected.title}</p>
                  <p className="text-sm text-gray-400">{selected.year ?? "—"}</p>
                  <p className="text-xs text-gray-500 line-clamp-3 mt-1">{selected.description}</p>
                </div>
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Заметки (необязательно)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setStep("candidates")}
                  className="flex-1 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
                >
                  ← Назад
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? "Добавление..." : "Добавить"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
