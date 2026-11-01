"""Add Stripe customer link + CV-tailoring credit ledger

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-11-01

Billing first slice (TSK-64): stripe_customer_id / credit_balance on user,
append-only ledger with unique idempotency keys. Free grant is applied in
app code (3 lifetime credits), not via a Stripe Product.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: str | Sequence[str] | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_user_stripe_customer_id"),
        "user",
        ["stripe_customer_id"],
        unique=True,
    )
    op.add_column(
        "user",
        sa.Column(
            "credit_balance",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "billing_credit_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=True),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_billing_credit_ledger_idem"),
    )
    op.create_index(
        op.f("ix_billing_credit_ledger_user_id"),
        "billing_credit_ledger",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_billing_credit_ledger_reason"),
        "billing_credit_ledger",
        ["reason"],
        unique=False,
    )
    op.create_index(
        op.f("ix_billing_credit_ledger_idempotency_key"),
        "billing_credit_ledger",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_billing_credit_ledger_stripe_event_id"),
        "billing_credit_ledger",
        ["stripe_event_id"],
        unique=False,
    )

    # Defense-in-depth for Data API (same pattern as other PII tables).
    op.execute('ALTER TABLE public."billing_credit_ledger" ENABLE ROW LEVEL SECURITY')
    op.execute(
        'REVOKE ALL ON TABLE public."billing_credit_ledger" FROM anon, authenticated'
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
        'public."billing_credit_ledger" TO service_role'
    )


def downgrade() -> None:
    op.execute('ALTER TABLE public."billing_credit_ledger" DISABLE ROW LEVEL SECURITY')
    op.drop_index(
        op.f("ix_billing_credit_ledger_stripe_event_id"),
        table_name="billing_credit_ledger",
    )
    op.drop_index(
        op.f("ix_billing_credit_ledger_idempotency_key"),
        table_name="billing_credit_ledger",
    )
    op.drop_index(
        op.f("ix_billing_credit_ledger_reason"),
        table_name="billing_credit_ledger",
    )
    op.drop_index(
        op.f("ix_billing_credit_ledger_user_id"),
        table_name="billing_credit_ledger",
    )
    op.drop_table("billing_credit_ledger")
    op.drop_column("user", "credit_balance")
    op.drop_index(op.f("ix_user_stripe_customer_id"), table_name="user")
    op.drop_column("user", "stripe_customer_id")
