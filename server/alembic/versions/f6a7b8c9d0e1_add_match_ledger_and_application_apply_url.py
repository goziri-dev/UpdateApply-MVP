"""add match_ledger and application.apply_url

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-25 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("posting_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("matched_title", sa.String(length=512), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["posting_id"], ["job_posting.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "posting_id",
            name="uq_match_ledger_user_posting",
        ),
    )
    op.create_index(
        op.f("ix_match_ledger_user_id"),
        "match_ledger",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_ledger_posting_id"),
        "match_ledger",
        ["posting_id"],
        unique=False,
    )

    op.add_column(
        "application",
        sa.Column("apply_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application", "apply_url")
    op.drop_index(op.f("ix_match_ledger_posting_id"), table_name="match_ledger")
    op.drop_index(op.f("ix_match_ledger_user_id"), table_name="match_ledger")
    op.drop_table("match_ledger")
