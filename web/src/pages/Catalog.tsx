import { useCallback, useEffect, useRef, useState } from "react";
import type { Media } from "../types";
import { api } from "../api";
import MediaCard from "../components/MediaCard";
import FilterBar from "../components/FilterBar";
import Pagination from "../components/Pagination";
import AddMediaModal from "../components/AddMediaModal";
import EditMediaModal from "../components/EditMediaModal";

interface Filters {
  category: string;
  type: string;
  watched_status: string;
  search: string;
}

const DEFAULT_FILTERS: Filters = { category: "", type: "", watched_status: "", search: "" };
const PAGE_SIZE = 24;

export default function Catalog() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Media[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState<Media | null>(null);
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
  }, [filters, page, load]);

  function handleFilterChange(newFilters: Filters) {
    setFilters(newFilters);
    setPage(1);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <FilterBar filters={filters} onChange={handleFilterChange} />
        <button
          onClick={() => setShowAdd(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700"
        >
          + Добавить
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">{error}</div>
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-12">Загрузка...</div>
      ) : items.length === 0 ? (
        <div className="text-center text-gray-400 py-12">Ничего не найдено</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {items.map((m) => (
            <MediaCard key={m.id} media={m} onEdit={setEditTarget} />
          ))}
        </div>
      )}

      <Pagination page={page} total={total} pageSize={PAGE_SIZE} onChange={setPage} />

      {showAdd && (
        <AddMediaModal
          onClose={() => setShowAdd(false)}
          onAdded={() => load(filters, page)}
        />
      )}

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
    </div>
  );
}
