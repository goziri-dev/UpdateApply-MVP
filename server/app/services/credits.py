"""CV-tailoring credit ledger: free grant, Stripe grants, tailor spends."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.models.billing_credit_ledger import BillingCreditLedger
from app.models.user import User


class InsufficientCreditsError(Exception):
    """Raised when a tailor would leave the balance below zero."""

    def __init__(self, balance: int, required: int = 1) -> None:
        self.balance = balance
        self.required = required
        super().__init__(
            f"Insufficient CV-tailoring credits ({balance} available, {required} required)."
        )


def _locked_user(session: Session, user_id: UUID) -> User:
    """Load user row with FOR UPDATE so balance updates stay atomic."""
    stmt = select(User).where(User.id == user_id).with_for_update()
    user = session.exec(stmt).one()
    return user


def free_grant_applied(session: Session, user_id: UUID) -> bool:
    key = f"free_grant:{user_id}"
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
    """Apply lifetime free credits once per account (Decision: 3)."""
    s = settings or get_settings()
    amount = max(0, int(s.stripe_free_credits))
    if amount <= 0:
        return user
    key = f"free_grant:{user.id}"
    if free_grant_applied(session, user.id):
        session.refresh(user)
        return user
    try:
        return apply_credit_delta(
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


def apply_credit_delta(
    session: Session,
    *,
    user_id: UUID,
    delta: int,
    reason: str,
    idempotency_key: str,
    stripe_event_id: str | None = None,
) -> User:
    """Idempotently adjust balance. Replays with the same key are no-ops."""
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
    new_balance = int(user.credit_balance) + int(delta)
    if new_balance < 0:
        raise InsufficientCreditsError(
            balance=int(user.credit_balance), required=-delta
        )

    user.credit_balance = new_balance
    user.updated_at = datetime.now(UTC)
    entry = BillingCreditLedger(
        user_id=user_id,
        delta=int(delta),
        reason=reason,
        idempotency_key=idempotency_key,
        stripe_event_id=stripe_event_id,
        balance_after=new_balance,
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
    return apply_credit_delta(
        session,
        user_id=user_id,
        delta=-1,
        reason="tailor",
        idempotency_key=f"tailor:{application_id}",
    )
