"""index job_posting active last_seen_at for match lookback

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-25

Jobs For You Pass 1 filters active rows by freshness (last_seen / vendor
stamps). A partial index keeps that scan cheap as the catalog grows.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_job_posting_active_last_seen_at",
        "job_posting",
        ["last_seen_at"],
        unique=False,
        postgresql_where="is_active IS TRUE",
    )
    op.create_index(
        "ix_job_posting_active_vendor_updated_at",
        "job_posting",
        ["vendor_updated_at"],
        unique=False,
        postgresql_where="is_active IS TRUE",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_posting_active_vendor_updated_at",
        table_name="job_posting",
        postgresql_where="is_active IS TRUE",
    )
    op.drop_index(
        "ix_job_posting_active_last_seen_at",
        table_name="job_posting",
        postgresql_where="is_active IS TRUE",
    )
