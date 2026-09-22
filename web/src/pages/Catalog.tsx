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
  const { addedCount, onAdd } = useOutletContext<CatalogOutletContext>();
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
          onClick={onAdd}
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
