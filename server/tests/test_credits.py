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
            self.assertEqual(user.wallet_credits, 3)
            self.assertEqual(user.period_credits, 0)
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
            self.assertEqual(user.wallet_credits, 2)
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

    def test_period_reset_preserves_wallet(self) -> None:
        with Session(self.engine) as session:
            user = self._user(session)
            user = credits_svc.ensure_free_grant(session, user, settings=self.settings)
            # Spend 1 free credit, then buy PAYG (+1 wallet).
            user = credits_svc.deduct_tailor_credit(
                session, user_id=user.id, application_id=uuid4()
            )
            user = credits_svc.apply_wallet_delta(
                session,
                user_id=user.id,
                delta=1,
                reason="payg",
                idempotency_key="stripe:checkout:test_payg",
            )
            self.assertEqual(user.wallet_credits, 3)  # 2 free left + 1 PAYG
            self.assertEqual(user.credit_balance, 3)

            # Lite period sets allotment to 10; wallet preserved → total 13.
            user = credits_svc.set_period_allotment(
                session,
                user_id=user.id,
                allotment=10,
                plan="lite",
                reason="lite_period",
                idempotency_key="stripe:sub_period:sub_1:100",
            )
            self.assertEqual(user.billing_plan, "lite")
            self.assertEqual(user.period_credits, 10)
            self.assertEqual(user.wallet_credits, 3)
            self.assertEqual(user.credit_balance, 13)

            # Spend 4 → period 6, wallet 3.
            for _ in range(4):
                user = credits_svc.deduct_tailor_credit(
                    session, user_id=user.id, application_id=uuid4()
                )
            self.assertEqual(user.period_credits, 6)
            self.assertEqual(user.wallet_credits, 3)
            self.assertEqual(user.credit_balance, 9)

            # Renewal resets period to 10 (no rollover of unused 6); wallet intact.
            user = credits_svc.set_period_allotment(
                session,
                user_id=user.id,
                allotment=10,
                plan="lite",
                reason="lite_period",
                idempotency_key="stripe:sub_period:sub_1:200",
            )
            self.assertEqual(user.period_credits, 10)
            self.assertEqual(user.wallet_credits, 3)
            self.assertEqual(user.credit_balance, 13)

            # Idempotent replay of same period key.
            user = credits_svc.set_period_allotment(
                session,
                user_id=user.id,
                allotment=10,
                plan="lite",
                reason="lite_period",
                idempotency_key="stripe:sub_period:sub_1:200",
            )
            self.assertEqual(user.credit_balance, 13)

    def test_spend_falls_through_to_wallet(self) -> None:
        with Session(self.engine) as session:
            user = self._user(session)
            user = credits_svc.apply_wallet_delta(
                session,
                user_id=user.id,
                delta=2,
                reason="payg",
                idempotency_key="payg:a",
            )
            user = credits_svc.set_period_allotment(
                session,
                user_id=user.id,
                allotment=1,
                plan="lite",
                reason="lite_period",
                idempotency_key="period:a",
            )
            self.assertEqual(user.credit_balance, 3)
            user = credits_svc.deduct_tailor_credit(
                session, user_id=user.id, application_id=uuid4()
            )
            self.assertEqual(user.period_credits, 0)
            self.assertEqual(user.wallet_credits, 2)
            user = credits_svc.deduct_tailor_credit(
                session, user_id=user.id, application_id=uuid4()
            )
            self.assertEqual(user.wallet_credits, 1)
            self.assertEqual(user.credit_balance, 1)


if __name__ == "__main__":
    unittest.main()
