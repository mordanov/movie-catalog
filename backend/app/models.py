import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MediaType(str, enum.Enum):
    movie = "movie"
    cartoon = "cartoon"
    series = "series"


class MediaCategory(str, enum.Enum):
    kids_series = "kids_series"
    adult_series = "adult_series"
    family_movie = "family_movie"
    adult_movie = "adult_movie"
    cartoon = "cartoon"


class CartoonSubtype(str, enum.Enum):
    disney = "disney"
    pixar = "pixar"
    soviet = "soviet"
    russian = "russian"
    other = "other"


class WatchedStatus(str, enum.Enum):
    not_watched = "not_watched"
    watching = "watching"
    watched = "watched"


class MediaSource(str, enum.Enum):
    telegram_text = "telegram_text"
    telegram_screenshot = "telegram_screenshot"
    web_ui = "web_ui"


class Media(Base):
    __tablename__ = "media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_ru: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type"), nullable=False
    )
    category: Mapped[MediaCategory] = mapped_column(
        Enum(MediaCategory, name="media_category"), nullable=False
    )
    cartoon_subtype: Mapped[CartoonSubtype | None] = mapped_column(
        Enum(CartoonSubtype, name="cartoon_subtype"), nullable=True
    )
    genres: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    actors: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    external_ids: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    rating_external: Mapped[float | None] = mapped_column(Float, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    watched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    watched_status: Mapped[WatchedStatus] = mapped_column(
        Enum(WatchedStatus, name="watched_status"),
        nullable=False,
        default=WatchedStatus.not_watched,
        server_default=text("'not_watched'"),
    )
    source: Mapped[MediaSource] = mapped_column(
        Enum(MediaSource, name="media_source"), nullable=False
    )
    added_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BotUser(Base):
    __tablename__ = "bot_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
