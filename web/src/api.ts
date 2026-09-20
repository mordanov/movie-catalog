import type { Candidate, Media, MediaListResponse, MediaUpdate, StatsResponse } from "./types";
import type { MediaCategory, MediaSource, CartoonSubtype } from "./types";

const BASE = "/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (resp.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new Error(`${resp.status}: ${text}`);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  auth: {
    login: (login: string, password: string) =>
      request<{ ok: boolean }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ login, password }),
      }),
    logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
    me: () => request<{ login: string }>("/auth/me"),
  },

  media: {
    list: (params: {
      page?: number;
      page_size?: number;
      category?: string;
      type?: string;
      watched_status?: string;
      search?: string;
    } = {}) => {
      const qs = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params)
            .filter(([, v]) => v !== undefined && v !== "")
            .map(([k, v]) => [k, String(v)])
        )
      ).toString();
      return request<MediaListResponse>(`/media${qs ? `?${qs}` : ""}`);
    },
    get: (id: string) => request<Media>(`/media/${id}`),
    update: (id: string, data: MediaUpdate) =>
      request<Media>(`/media/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/media/${id}`, { method: "DELETE" }),
    random: (params: { category?: string; type?: string } = {}) => {
      const qs = new URLSearchParams(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v))
      ).toString();
      return request<Media>(`/media/random${qs ? `?${qs}` : ""}`);
    },
    confirm: (data: {
      tmdb_id: number;
      media_type: string;
      category: MediaCategory;
      cartoon_subtype?: CartoonSubtype | null;
      source: MediaSource;
      notes?: string;
    }) => request<Media>("/media/confirm", { method: "POST", body: JSON.stringify(data) }),
  },

  resolve: {
    search: (query: string) =>
      request<Candidate[]>("/resolve", { method: "POST", body: JSON.stringify({ query }) }),
    byScreenshot: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch(`${BASE}/resolve/screenshot`, { method: "POST", credentials: "include", body: fd });
      if (r.status === 401) { window.location.href = "/login"; throw new Error("Unauthorized"); }
      if (!r.ok) throw new Error(`${r.status}`);
      return r.json() as Promise<Candidate[]>;
    },
  },

  stats: {
    get: () => request<StatsResponse>("/stats"),
  },
};
