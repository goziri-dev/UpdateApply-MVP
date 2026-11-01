"""Enable RLS + revoke Data API grants on user PII tables

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-11-01

Defense-in-depth for Supabase PostgREST / Data API. Mirrors waitlist /
allowlist: ENABLE ROW LEVEL SECURITY with no public policies, REVOKE from
anon/authenticated, GRANT to service_role.

FastAPI still connects via DATABASE_URL (privileged role that bypasses RLS),
so app-layer ``user_id`` checks remain the primary isolation guarantee.
See Docs Decision: owner-scoped PII isolation (app-layer + Data API revoke).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: str | Sequence[str] | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# User-scoped PII / personalization tables. Shared catalog
# (company_board, job_posting) intentionally excluded.
_PII_TABLES: tuple[str, ...] = (
    "user",
    "profile",
    "application",
    "profile_chunk",
    "match_preference",
    "match_ledger",
    "match_notification",
)


def upgrade() -> None:
    for table in _PII_TABLES:
        # Quote identifiers — ``user`` is a reserved word.
        qualified = f'public."{table}"'
        op.execute(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON TABLE {qualified} FROM anon, authenticated")
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {qualified} TO service_role"
        )


def downgrade() -> None:
    # Best-effort rollback: disable RLS. Re-granting anon/authenticated is
    # intentionally omitted — prefer staying locked down after a downgrade.
    for table in _PII_TABLES:
        qualified = f'public."{table}"'
        op.execute(f"ALTER TABLE {qualified} DISABLE ROW LEVEL SECURITY")
