export type MediaType = "movie" | "cartoon" | "series";

export type MediaCategory =
  | "kids_series"
  | "adult_series"
  | "family_movie"
  | "adult_movie"
  | "cartoon";

export type CartoonSubtype = "disney" | "pixar" | "soviet" | "russian" | "other";

export type WatchedStatus = "not_watched" | "watching" | "watched";

export type MediaSource = "telegram_text" | "telegram_screenshot" | "web_ui";

export interface Media {
  id: string;
  title: string;
  title_ru: string | null;
  year: number | null;
  description: string | null;
  poster_url: string | null;
  type: MediaType;
  category: MediaCategory;
  cartoon_subtype: CartoonSubtype | null;
  genres: string[];
  actors: string[];
  external_ids: Record<string, unknown>;
  rating_external: number | null;
  added_at: string;
  watched_at: string | null;
  watched_status: WatchedStatus;
  source: MediaSource;
  added_by: string | null;
  notes: string | null;
  trailer_url: string | null;
}

export interface MediaListResponse {
  items: Media[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  total: number;
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  by_watched_status: Record<string, number>;
}

export interface Candidate {
  tmdb_id: number;
  media_type: string;
  title: string;
  title_ru: string | null;
  year: number | null;
  description: string | null;
  poster_url: string | null;
  genres: string[];
  rating: number | null;
  disambiguation_question: string | null;
}

export interface GenresResponse {
  genres: string[];
}

export interface MediaUpdate {
  title?: string;
  title_ru?: string;
  year?: number;
  description?: string;
  category?: MediaCategory;
  cartoon_subtype?: CartoonSubtype | null;
  watched_status?: WatchedStatus;
  notes?: string;
}
