"""add application table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-24 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company", sa.String(), nullable=False, server_default=""),
        sa.Column("target_role", sa.String(), nullable=False, server_default=""),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column(
            "resume_document",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_user_id"),
        "application",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_company"),
        "application",
        ["company"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_target_role"),
        "application",
        ["target_role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_status"),
        "application",
        ["status"],
        unique=False,
    )
    # No unique on (user_id, company, target_role) — versions are separate rows.


def downgrade() -> None:
    op.drop_index(op.f("ix_application_status"), table_name="application")
    op.drop_index(op.f("ix_application_target_role"), table_name="application")
    op.drop_index(op.f("ix_application_company"), table_name="application")
    op.drop_index(op.f("ix_application_user_id"), table_name="application")
    op.drop_table("application")
