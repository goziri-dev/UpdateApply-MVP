"""Idempotent CV-tailoring credit ledger (Stripe grants + tailor spends)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class BillingCreditLedger(SQLModel, table=True):
    """Append-only credit movements. ``idempotency_key`` prevents double-apply."""

    # pyrefly: ignore[bad-override]
    __tablename__ = "billing_credit_ledger"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    # Positive = grant; negative = spend.
    delta: int
    # free_grant | payg | lite_period | plus_period | tailor | adjust
    reason: str = Field(max_length=64, index=True)
    idempotency_key: str = Field(max_length=255, unique=True, index=True)
    stripe_event_id: str | None = Field(default=None, max_length=255, index=True)
    balance_after: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
