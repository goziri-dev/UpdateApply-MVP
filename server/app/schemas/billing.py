"""Billing request/response schemas (Checkout + balance)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CheckoutPlan = Literal["payg", "lite", "plus"]


class CheckoutSessionRequest(BaseModel):
    plan: CheckoutPlan


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str
    plan: CheckoutPlan


class PortalSessionResponse(BaseModel):
    portal_url: str


class CreditBalanceResponse(BaseModel):
    user_id: UUID
    credit_balance: int
    stripe_customer_id: str | None = None
    free_grant_applied: bool = False
    plans: dict[str, str] = Field(
        default_factory=dict,
        description="Configured Stripe price IDs by plan code (payg/lite/plus).",
    )


class CreditLedgerEntry(BaseModel):
    id: UUID
    delta: int
    reason: str
    balance_after: int
    created_at: datetime
