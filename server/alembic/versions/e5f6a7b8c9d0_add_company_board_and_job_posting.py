"""add company_board and job_posting tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-25 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMBEDDING_DIMS = 1536


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    op.create_table(
        "company_board",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vendor", sa.String(length=32), nullable=False),
        sa.Column("slug", sa.String(length=256), nullable=False),
        sa.Column("company_name", sa.String(length=512), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="seed",
        ),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "vendor IN ('greenhouse', 'lever', 'ashby')",
            name="ck_company_board_vendor",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'unavailable', 'disabled')",
            name="ck_company_board_status",
        ),
        sa.CheckConstraint(
            "source IN ('seed', 'user')",
            name="ck_company_board_source",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vendor", "slug", name="uq_company_board_vendor_slug"),
    )
    op.create_index(
        op.f("ix_company_board_vendor"),
        "company_board",
        ["vendor"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_board_slug"),
        "company_board",
        ["slug"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_board_status"),
        "company_board",
        ["status"],
        unique=False,
    )

    op.create_table(
        "job_posting",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("vendor", sa.String(length=32), nullable=False),
        sa.Column("external_job_id", sa.String(length=256), nullable=False),
        sa.Column(
            "company_name",
            sa.String(length=512),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "title",
            sa.String(length=1024),
            nullable=False,
            server_default="",
        ),
        sa.Column("location_raw", sa.Text(), nullable=False, server_default=""),
        sa.Column("location_remote", sa.Boolean(), nullable=True),
        sa.Column(
            "location_countries",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("location_parse_status", sa.String(length=32), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column(
            "description_truncated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("vendor_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vendor_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding", Vector(_EMBEDDING_DIMS), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "vendor IN ('greenhouse', 'lever', 'ashby')",
            name="ck_job_posting_vendor",
        ),
        sa.ForeignKeyConstraint(["board_id"], ["company_board.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "vendor",
            "external_job_id",
            name="uq_job_posting_vendor_external_job_id",
        ),
    )
    op.create_index(
        op.f("ix_job_posting_board_id"),
        "job_posting",
        ["board_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_posting_vendor"),
        "job_posting",
        ["vendor"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_posting_external_job_id"),
        "job_posting",
        ["external_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_posting_is_active"),
        "job_posting",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_job_posting_is_active"), table_name="job_posting")
    op.drop_index(op.f("ix_job_posting_external_job_id"), table_name="job_posting")
    op.drop_index(op.f("ix_job_posting_vendor"), table_name="job_posting")
    op.drop_index(op.f("ix_job_posting_board_id"), table_name="job_posting")
    op.drop_table("job_posting")

    op.drop_index(op.f("ix_company_board_status"), table_name="company_board")
    op.drop_index(op.f("ix_company_board_slug"), table_name="company_board")
    op.drop_index(op.f("ix_company_board_vendor"), table_name="company_board")
    op.drop_table("company_board")
