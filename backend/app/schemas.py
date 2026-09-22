import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import (
    CartoonSubtype,
    MediaCategory,
    MediaSource,
    MediaType,
    WatchedStatus,
)


class MediaCreate(BaseModel):
    title: str
    title_ru: str | None = None
    year: int | None = None
    description: str | None = None
    poster_url: str | None = None
    type: MediaType
    category: MediaCategory
    cartoon_subtype: CartoonSubtype | None = None
    genres: list[str] = []
    actors: list[str] = []
    external_ids: dict = {}
    rating_external: float | None = None
    watched_status: WatchedStatus = WatchedStatus.not_watched
    source: MediaSource
    added_by: str | None = None
    notes: str | None = None
    trailer_url: str | None = None


class MediaUpdate(BaseModel):
    title: str | None = None
    title_ru: str | None = None
    year: int | None = None
    description: str | None = None
    poster_url: str | None = None
    type: MediaType | None = None
    category: MediaCategory | None = None
    cartoon_subtype: CartoonSubtype | None = None
    genres: list[str] | None = None
    actors: list[str] | None = None
    rating_external: float | None = None
    watched_status: WatchedStatus | None = None
    watched_at: datetime | None = None
    notes: str | None = None
    trailer_url: str | None = None


class MediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    title_ru: str | None
    year: int | None
    description: str | None
    poster_url: str | None
    type: MediaType
    category: MediaCategory
    cartoon_subtype: CartoonSubtype | None
    genres: list[str]
    actors: list[str]
    external_ids: dict
    rating_external: float | None
    added_at: datetime
    watched_at: datetime | None
    watched_status: WatchedStatus
    source: MediaSource
    added_by: str | None
    notes: str | None
    trailer_url: str | None


class MediaListResponse(BaseModel):
    items: list[MediaResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    by_category: dict[str, int]
    by_watched_status: dict[str, int]


class CandidateResponse(BaseModel):
    tmdb_id: int
    media_type: str  # "movie" or "tv"
    title: str
    title_ru: str | None
    year: int | None
    description: str | None
    poster_url: str | None
    genres: list[str]
    rating: float | None
    disambiguation_question: str | None = None
