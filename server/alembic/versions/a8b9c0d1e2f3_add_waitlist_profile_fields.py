"""add waitlist name, career_stage, job_search_challenges

Revision ID: a8b9c0d1e2f3
Revises: d0e1f2a3b4c5
Create Date: 2026-10-27

Enrich marketing waitlist capture for Favour's review + Google Sheet sync.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: str | Sequence[str] | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.waitlist_signup ADD COLUMN IF NOT EXISTS name text NULL"
    )
    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "ADD COLUMN IF NOT EXISTS career_stage text NULL"
    )
    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "ADD COLUMN IF NOT EXISTS job_search_challenges text NULL"
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'waitlist_signup_career_stage_chk'
          ) THEN
            ALTER TABLE public.waitlist_signup
              ADD CONSTRAINT waitlist_signup_career_stage_chk
              CHECK (
                career_stage IS NULL
                OR career_stage IN (
                  'student',
                  'early_career',
                  'mid_career',
                  'senior',
                  'career_changer',
                  'other'
                )
              );
          END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.waitlist_signup "
        "DROP CONSTRAINT IF EXISTS waitlist_signup_career_stage_chk"
    )
    op.execute(
        "ALTER TABLE public.waitlist_signup DROP COLUMN IF EXISTS job_search_challenges"
    )
    op.execute("ALTER TABLE public.waitlist_signup DROP COLUMN IF EXISTS career_stage")
    op.execute("ALTER TABLE public.waitlist_signup DROP COLUMN IF EXISTS name")
