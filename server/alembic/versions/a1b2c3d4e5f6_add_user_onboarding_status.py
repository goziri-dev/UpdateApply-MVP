"""add user onboarding_status

Revision ID: a1b2c3d4e5f6
Revises: 6e828c3bb296
Create Date: 2026-10-20 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "6e828c3bb296"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "onboarding_status",
            sa.String(),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.create_index(
        op.f("ix_user_onboarding_status"),
        "user",
        ["onboarding_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_onboarding_status"), table_name="user")
    op.drop_column("user", "onboarding_status")
