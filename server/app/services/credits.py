"""CV-tailoring credit ledger: free grant, Stripe grants, tailor spends.

Bucket model (TSK-65 / Decision):
- ``wallet_credits``: lifetime free + PAYG (never period-reset)
- ``period_credits``: Lite/Plus monthly allotment (reset each billing period;
  unused period credits do not roll over)
- ``credit_balance``: denormalized wallet + period (API / enforcement)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.models.billing_credit_ledger import BillingCreditLedger
from app.models.user import User

BillingPlan = Literal["free", "lite", "plus"]


class InsufficientCreditsError(Exception):
    """Raised when a tailor would leave the balance below zero."""

    def __init__(self, balance: int, required: int = 1) -> None:
        self.balance = balance
        self.required = required
        super().__init__(
            f"Insufficient CV-tailoring credits ({balance} available, {required} required)."
        )


def free_grant_key(user_id: UUID) -> str:
    """Stable lifetime free-grant idempotency key (v1)."""
    return f"free_grant:{user_id}"


def _locked_user(session: Session, user_id: UUID) -> User:
    """Load user row with FOR UPDATE so balance updates stay atomic."""
    stmt = select(User).where(User.id == user_id).with_for_update()
    user = session.exec(stmt).one()
    return user


def _sync_balance(user: User) -> None:
    user.wallet_credits = max(0, int(user.wallet_credits))
    user.period_credits = max(0, int(user.period_credits))
    user.credit_balance = int(user.wallet_credits) + int(user.period_credits)


def free_grant_applied(session: Session, user_id: UUID) -> bool:
    key = free_grant_key(user_id)
    row = session.exec(
        select(BillingCreditLedger).where(BillingCreditLedger.idempotency_key == key)
    ).first()
    return row is not None


def ensure_free_grant(
    session: Session,
    user: User,
    *,
    settings: Settings | None = None,
) -> User:
    """Apply lifetime free credits once per account (Decision: 3 → wallet)."""
    s = settings or get_settings()
    amount = max(0, int(s.stripe_free_credits))
    if amount <= 0:
        return user
    key = free_grant_key(user.id)
    if free_grant_applied(session, user.id):
        session.refresh(user)
        return user
    try:
        return apply_wallet_delta(
            session,
            user_id=user.id,
            delta=amount,
            reason="free_grant",
            idempotency_key=key,
        )
    except IntegrityError:
        session.rollback()
        refreshed = session.get(User, user.id)
        assert refreshed is not None
        return refreshed


def apply_wallet_delta(
    session: Session,
    *,
    user_id: UUID,
    delta: int,
    reason: str,
    idempotency_key: str,
    stripe_event_id: str | None = None,
) -> User:
    """Idempotently adjust wallet credits (free / PAYG)."""
    existing = session.exec(
        select(BillingCreditLedger).where(
            BillingCreditLedger.idempotency_key == idempotency_key
        )
    ).first()
    if existing is not None:
        user = session.get(User, user_id)
        if user is None:
            raise LookupError(f"user {user_id} missing")
        return user

    user = _locked_user(session, user_id)
    new_wallet = int(user.wallet_credits) + int(delta)
    if new_wallet < 0:
        raise InsufficientCreditsError(
            balance=int(user.credit_balance), required=-delta
        )

    user.wallet_credits = new_wallet
    _sync_balance(user)
    user.updated_at = datetime.now(UTC)
    entry = BillingCreditLedger(
        user_id=user_id,
        delta=int(delta),
        reason=reason,
        idempotency_key=idempotency_key,
        stripe_event_id=stripe_event_id,
        balance_after=int(user.credit_balance),
    )
    session.add(user)
    session.add(entry)
    session.commit()
    session.refresh(user)
    return user


def set_period_allotment(
    session: Session,
    *,
    user_id: UUID,
    allotment: int,
    plan: BillingPlan,
    reason: str,
    idempotency_key: str,
    stripe_event_id: str | None = None,
) -> User:
    """Reset period credits to ``allotment`` (no rollover) and set billing plan.

    Wallet credits are preserved. Ledger ``delta`` is the change in total balance.
    """
    existing = session.exec(
        select(BillingCreditLedger).where(
            BillingCreditLedger.idempotency_key == idempotency_key
        )
    ).first()
    if existing is not None:
        user = session.get(User, user_id)
        if user is None:
            raise LookupError(f"user {user_id} missing")
        return user

    amount = max(0, int(allotment))
    user = _locked_user(session, user_id)
    old_balance = int(user.credit_balance)
    user.period_credits = amount
    user.billing_plan = plan
    _sync_balance(user)
    user.updated_at = datetime.now(UTC)
    delta = int(user.credit_balance) - old_balance
    entry = BillingCreditLedger(
        user_id=user_id,
        delta=delta,
        reason=reason,
        idempotency_key=idempotency_key,
        stripe_event_id=stripe_event_id,
        balance_after=int(user.credit_balance),
    )
    session.add(user)
    session.add(entry)
    session.commit()
    session.refresh(user)
    return user


def clear_subscription_period(
    session: Session,
    *,
    user_id: UUID,
    idempotency_key: str,
    stripe_event_id: str | None = None,
) -> User:
    """On cancel/delete: drop period credits and return plan to free."""
    return set_period_allotment(
        session,
        user_id=user_id,
        allotment=0,
        plan="free",
        reason="subscription_ended",
        idempotency_key=idempotency_key,
        stripe_event_id=stripe_event_id,
    )


def apply_credit_delta(
    session: Session,
    *,
    user_id: UUID,
    delta: int,
    reason: str,
    idempotency_key: str,
    stripe_event_id: str | None = None,
) -> User:
    """Backward-compatible wallet/total adjust (PAYG / free / generic).

    Prefer ``apply_wallet_delta`` / ``set_period_allotment`` for new callers.
    Positive deltas go to wallet; negative spend period-first then wallet.
    """
    if delta >= 0:
        return apply_wallet_delta(
            session,
            user_id=user_id,
            delta=delta,
            reason=reason,
            idempotency_key=idempotency_key,
            stripe_event_id=stripe_event_id,
        )
    return _spend_credits(
        session,
        user_id=user_id,
        amount=-int(delta),
        reason=reason,
        idempotency_key=idempotency_key,
        stripe_event_id=stripe_event_id,
    )


def _spend_credits(
    session: Session,
    *,
    user_id: UUID,
    amount: int,
    reason: str,
    idempotency_key: str,
    stripe_event_id: str | None = None,
) -> User:
    existing = session.exec(
        select(BillingCreditLedger).where(
            BillingCreditLedger.idempotency_key == idempotency_key
        )
    ).first()
    if existing is not None:
        user = session.get(User, user_id)
        if user is None:
            raise LookupError(f"user {user_id} missing")
        return user

    need = max(0, int(amount))
    user = _locked_user(session, user_id)
    if int(user.credit_balance) < need:
        raise InsufficientCreditsError(balance=int(user.credit_balance), required=need)

    # Spend period allotment first, then wallet (Decision: monthly then top-ups).
    from_period = min(int(user.period_credits), need)
    user.period_credits = int(user.period_credits) - from_period
    remaining = need - from_period
    if remaining:
        user.wallet_credits = int(user.wallet_credits) - remaining
    _sync_balance(user)
    user.updated_at = datetime.now(UTC)
    entry = BillingCreditLedger(
        user_id=user_id,
        delta=-need,
        reason=reason,
        idempotency_key=idempotency_key,
        stripe_event_id=stripe_event_id,
        balance_after=int(user.credit_balance),
    )
    session.add(user)
    session.add(entry)
    session.commit()
    session.refresh(user)
    return user


def require_credit_for_tailor(
    session: Session,
    user: User,
    *,
    settings: Settings | None = None,
) -> User:
    """Ensure free grant, then require at least 1 credit before calling Tailor LLM."""
    user = ensure_free_grant(session, user, settings=settings)
    if int(user.credit_balance) < 1:
        raise InsufficientCreditsError(balance=int(user.credit_balance), required=1)
    return user


def deduct_tailor_credit(
    session: Session,
    *,
    user_id: UUID,
    application_id: UUID,
) -> User:
    """Spend 1 credit after a successful tailor that persisted an application."""
    return _spend_credits(
        session,
        user_id=user_id,
        amount=1,
        reason="tailor",
        idempotency_key=f"tailor:{application_id}",
    )
