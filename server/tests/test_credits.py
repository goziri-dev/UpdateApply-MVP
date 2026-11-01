"""Unit tests for CV-tailoring credit ledger (no Stripe network)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings
from app.models.billing_credit_ledger import BillingCreditLedger
from app.models.user import User
from app.services import credits as credits_svc


class CreditsLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(
            self.engine,
            tables=[User.__table__, BillingCreditLedger.__table__],
        )
        self.settings = Settings(
            stripe_free_credits=3,
            stripe_secret_key="",
        )

    def _user(self, session: Session) -> User:
        user = User(
            id=uuid4(),
            oauth_subject=str(uuid4()),
            email="tester@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def test_free_grant_once(self) -> None:
        with Session(self.engine) as session:
            user = self._user(session)
            user = credits_svc.ensure_free_grant(session, user, settings=self.settings)
            self.assertEqual(user.credit_balance, 3)
            user = credits_svc.ensure_free_grant(session, user, settings=self.settings)
            self.assertEqual(user.credit_balance, 3)

    def test_deduct_tailor_idempotent(self) -> None:
        with Session(self.engine) as session:
            user = self._user(session)
            user = credits_svc.ensure_free_grant(session, user, settings=self.settings)
            app_id = uuid4()
            user = credits_svc.deduct_tailor_credit(
                session, user_id=user.id, application_id=app_id
            )
            self.assertEqual(user.credit_balance, 2)
            user = credits_svc.deduct_tailor_credit(
                session, user_id=user.id, application_id=app_id
            )
            self.assertEqual(user.credit_balance, 2)

    def test_insufficient_credits(self) -> None:
        with Session(self.engine) as session:
            user = self._user(session)
            zero_free = Settings(stripe_free_credits=0, stripe_secret_key="")
            with self.assertRaises(credits_svc.InsufficientCreditsError):
                credits_svc.require_credit_for_tailor(session, user, settings=zero_free)


if __name__ == "__main__":
    unittest.main()
