"""initial schema

Revision ID: 001initial
Revises:
Create Date: 2026-09-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE media_type AS ENUM ('movie', 'cartoon', 'series')")
    op.execute("CREATE TYPE media_category AS ENUM ('kids_series', 'adult_series', 'family_movie', 'adult_movie', 'cartoon')")
    op.execute("CREATE TYPE cartoon_subtype AS ENUM ('disney', 'pixar', 'soviet', 'russian', 'other')")
    op.execute("CREATE TYPE watched_status AS ENUM ('not_watched', 'watching', 'watched')")
    op.execute("CREATE TYPE media_source AS ENUM ('telegram_text', 'telegram_screenshot', 'web_ui')")

    op.create_table(
        "media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("title_ru", sa.String(500), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("poster_url", sa.String(2048), nullable=True),
        sa.Column("type", postgresql.ENUM(name="media_type", create_type=False), nullable=False),
        sa.Column("category", postgresql.ENUM(name="media_category", create_type=False), nullable=False),
        sa.Column("cartoon_subtype", postgresql.ENUM(name="cartoon_subtype", create_type=False), nullable=True),
        sa.Column("genres", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("actors", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("external_ids", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("rating_external", sa.Float, nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("watched_status", postgresql.ENUM(name="watched_status", create_type=False), nullable=False, server_default="'not_watched'"),
        sa.Column("source", postgresql.ENUM(name="media_source", create_type=False), nullable=False),
        sa.Column("added_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_table(
        "bot_users",
        sa.Column("telegram_id", sa.BigInteger, primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("added_by_telegram_id", sa.BigInteger, nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("media")
    op.drop_table("bot_users")
    for t in ("media_type", "media_category", "cartoon_subtype", "watched_status", "media_source"):
        op.execute(f"DROP TYPE {t}")
