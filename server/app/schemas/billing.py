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
    wallet_credits: int = 0
    period_credits: int = 0
    billing_plan: str = "free"
    stripe_customer_id: str | None = None
    free_grant_applied: bool = False
    tier_matrix: dict[str, str] = Field(
        default_factory=dict,
        description="Documented freemium ceilings (Decision / TSK-65).",
    )
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
