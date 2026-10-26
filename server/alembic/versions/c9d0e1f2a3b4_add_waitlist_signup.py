"""add waitlist_signup for marketing email capture

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-26

Marketing waitlist only — unique normalized email, RLS with no public
policies (server inserts via DATABASE_URL / service role).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotent: table may already exist if applied via Supabase MCP first.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.waitlist_signup (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          email text NOT NULL,
          source text NULL,
          ip text NULL,
          user_agent text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT waitlist_signup_email_lower_chk CHECK (email = lower(email)),
          CONSTRAINT waitlist_signup_email_key UNIQUE (email)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_waitlist_signup_created_at "
        "ON public.waitlist_signup (created_at DESC)"
    )
    op.execute("ALTER TABLE public.waitlist_signup ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE public.waitlist_signup FROM anon, authenticated")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
        "public.waitlist_signup TO service_role"
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_signup_created_at", table_name="waitlist_signup")
    op.drop_table("waitlist_signup")
