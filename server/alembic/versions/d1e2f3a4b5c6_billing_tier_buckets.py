"""Add wallet/period credit buckets + billing_plan (TSK-65)

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-11-01

Tier quotas: wallet_credits hold lifetime free + PAYG (never period-reset);
period_credits hold Lite/Plus allotment and reset each billing period.
billing_plan tracks free|lite|plus. credit_balance stays denormalized
(wallet + period).

Also backfills the lifetime free grant (3) for accounts that never received
it and have no paid ledger activity — idempotent via free_grant:{user_id}.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.sql import column, table

from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "c0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FREE_CREDITS = 3


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "wallet_credits",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "period_credits",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "billing_plan",
            sa.String(length=32),
            nullable=False,
            server_default="free",
        ),
    )
    op.create_index(
        op.f("ix_user_billing_plan"),
        "user",
        ["billing_plan"],
        unique=False,
    )

    # Existing single-pool balances become wallet (lifetime/PAYG semantics).
    op.execute(
        sa.text(
            'UPDATE "user" SET wallet_credits = credit_balance, '
            "period_credits = 0 WHERE credit_balance <> 0"
        )
    )

    conn = op.get_bind()
    users = conn.execute(
        sa.text(
            """
            SELECT u.id
            FROM "user" u
            WHERE NOT EXISTS (
                SELECT 1 FROM billing_credit_ledger l
                WHERE l.user_id = u.id
                  AND l.idempotency_key = 'free_grant:' || u.id::text
            )
              AND NOT EXISTS (
                SELECT 1 FROM billing_credit_ledger l
                WHERE l.user_id = u.id
                  AND l.reason IN ('payg', 'lite_period', 'plus_period')
              )
              AND u.credit_balance = 0
            """
        )
    ).fetchall()

    user_t = table(
        "user",
        column("id", sa.Uuid()),
        column("credit_balance", sa.Integer()),
        column("wallet_credits", sa.Integer()),
        column("period_credits", sa.Integer()),
        column("updated_at", sa.DateTime(timezone=True)),
    )
    ledger_t = table(
        "billing_credit_ledger",
        column("id", sa.Uuid()),
        column("user_id", sa.Uuid()),
        column("delta", sa.Integer()),
        column("reason", sa.String()),
        column("idempotency_key", sa.String()),
        column("stripe_event_id", sa.String()),
        column("balance_after", sa.Integer()),
        column("created_at", sa.DateTime(timezone=True)),
    )

    import uuid
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    for (user_id,) in users:
        key = f"free_grant:{user_id}"
        conn.execute(
            ledger_t.insert().values(
                id=uuid.uuid4(),
                user_id=user_id,
                delta=FREE_CREDITS,
                reason="free_grant",
                idempotency_key=key,
                stripe_event_id=None,
                balance_after=FREE_CREDITS,
                created_at=now,
            )
        )
        conn.execute(
            user_t.update()
            .where(user_t.c.id == user_id)
            .values(
                wallet_credits=FREE_CREDITS,
                period_credits=0,
                credit_balance=FREE_CREDITS,
                updated_at=now,
            )
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_billing_plan"), table_name="user")
    op.drop_column("user", "billing_plan")
    op.drop_column("user", "period_credits")
    op.drop_column("user", "wallet_credits")
