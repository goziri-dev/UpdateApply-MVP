"""add profile_chunk pgvector table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-23 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMBEDDING_DIMS = 1536


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    op.create_table(
        "profile_chunk",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_type", sa.String(length=64), nullable=False),
        sa.Column("source_item_id", sa.String(length=128), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(_EMBEDDING_DIMS), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profile.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_profile_chunk_user_id"), "profile_chunk", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_profile_chunk_profile_id"),
        "profile_chunk",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_profile_chunk_chunk_type"),
        "profile_chunk",
        ["chunk_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_profile_chunk_source_item_id"),
        "profile_chunk",
        ["source_item_id"],
        unique=False,
    )
    # Cosine distance ANN index — fine for MVP user-scoped top-k.
    op.execute(
        sa.text(
            "CREATE INDEX ix_profile_chunk_embedding_cosine "
            "ON profile_chunk USING hnsw (embedding vector_cosine_ops)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_profile_chunk_embedding_cosine"))
    op.drop_index(op.f("ix_profile_chunk_source_item_id"), table_name="profile_chunk")
    op.drop_index(op.f("ix_profile_chunk_chunk_type"), table_name="profile_chunk")
    op.drop_index(op.f("ix_profile_chunk_profile_id"), table_name="profile_chunk")
    op.drop_index(op.f("ix_profile_chunk_user_id"), table_name="profile_chunk")
    op.drop_table("profile_chunk")
