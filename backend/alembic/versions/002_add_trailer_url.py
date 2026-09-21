"""add trailer_url to media

Revision ID: 002trailer
Revises: 001initial
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002trailer"
down_revision: str | None = "001initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("media", sa.Column("trailer_url", sa.String(2048), nullable=True))


def downgrade() -> None:
    op.drop_column("media", "trailer_url")
