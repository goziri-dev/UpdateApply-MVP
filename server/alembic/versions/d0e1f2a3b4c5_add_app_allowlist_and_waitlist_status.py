"""add app_allowlist + waitlist review status

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-10-26

Allowlist gates app access after Supabase auth. Waitlist status tracks
Favour's review; approving inserts/reactivates an allowlist row.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.app_allowlist (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          email text NOT NULL,
          user_id uuid NULL,
          note text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          created_by text NULL,
          revoked_at timestamptz NULL,
          CONSTRAINT app_allowlist_email_lower_chk CHECK (email = lower(email)),
          CONSTRAINT app_allowlist_email_key UNIQUE (email)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_app_allowlist_email_active "
        "ON public.app_allowlist (email) WHERE revoked_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_app_allowlist_user_id "
        "ON public.app_allowlist (user_id) WHERE user_id IS NOT NULL"
    )
    op.execute("ALTER TABLE public.app_allowlist ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE public.app_allowlist FROM anon, authenticated")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
        "public.app_allowlist TO service_role"
    )

    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending'"
    )
    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "ADD COLUMN IF NOT EXISTS reviewed_at timestamptz NULL"
    )
    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "ADD COLUMN IF NOT EXISTS reviewed_by text NULL"
    )
    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "ADD COLUMN IF NOT EXISTS review_note text NULL"
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'waitlist_signup_status_chk'
          ) THEN
            ALTER TABLE public.waitlist_signup
              ADD CONSTRAINT waitlist_signup_status_chk
              CHECK (status IN ('pending', 'approved', 'rejected'));
          END IF;
        END $$
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_waitlist_signup_status "
        "ON public.waitlist_signup (status, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_waitlist_signup_status")
    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "DROP CONSTRAINT IF EXISTS waitlist_signup_status_chk"
    )
    op.execute("ALTER TABLE public.waitlist_signup DROP COLUMN IF EXISTS review_note")
    op.execute("ALTER TABLE public.waitlist_signup DROP COLUMN IF EXISTS reviewed_by")
    op.execute("ALTER TABLE public.waitlist_signup DROP COLUMN IF EXISTS reviewed_at")
    op.execute("ALTER TABLE public.waitlist_signup DROP COLUMN IF EXISTS status")
    op.execute("DROP INDEX IF EXISTS ix_app_allowlist_user_id")
    op.execute("DROP INDEX IF EXISTS ix_app_allowlist_email_active")
    op.execute("DROP TABLE IF EXISTS public.app_allowlist")
