"""add match_notification for Phase 3 in-app notify log

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-25 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_notification",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("posting_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("company", sa.String(length=512), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["posting_id"], ["job_posting.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "posting_id",
            name="uq_match_notification_user_posting",
        ),
    )
    op.create_index(
        op.f("ix_match_notification_user_id"),
        "match_notification",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_notification_posting_id"),
        "match_notification",
        ["posting_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_match_notification_posting_id"),
        table_name="match_notification",
    )
    op.drop_index(
        op.f("ix_match_notification_user_id"), table_name="match_notification"
    )
    op.drop_table("match_notification")
