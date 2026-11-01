"""Stripe Checkout, Customer Portal, balance, and webhook endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CreditBalanceResponse,
    PortalSessionResponse,
)
from app.services import credits as credits_svc
from app.services import stripe_billing as stripe_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _stripe_or_503() -> None:
    if not get_settings().stripe_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "stripe_not_configured",
                "message": (
                    "Billing is not configured on this server. "
                    "Set STRIPE_SECRET_KEY (and related STRIPE_* vars)."
                ),
            },
        )


@router.get("/balance", response_model=CreditBalanceResponse)
def get_balance(
    user: DbUser,
    session: SessionDep,
    settings: SettingsDep,
) -> CreditBalanceResponse:
    """Return CV-tailoring credit balance (applies lifetime free grant if needed)."""
    # Balance works without Stripe keys (free grant only); Checkout needs Stripe.
    user = credits_svc.ensure_free_grant(session, user, settings=settings)
    return CreditBalanceResponse(
        user_id=user.id,
        credit_balance=int(user.credit_balance),
        stripe_customer_id=user.stripe_customer_id,
        free_grant_applied=credits_svc.free_grant_applied(session, user.id),
        plans={
            "payg": settings.stripe_price_payg,
            "lite": settings.stripe_price_lite,
            "plus": settings.stripe_price_plus,
        },
    )


@router.get("/status")
def billing_status(settings: SettingsDep) -> dict[str, object]:
    """Non-secret health for ops: configured flags + mode mismatch (no key values)."""
    return {
        "stripe_configured": settings.stripe_configured,
        "webhook_secret_configured": bool(settings.stripe_webhook_secret.strip()),
        "secret_kind": (
            "live"
            if settings.stripe_secret_is_live
            else "test"
            if settings.stripe_secret_is_test
            else "other_or_empty"
        ),
        "mode_mismatch": settings.stripe_mode_mismatch,
        "prices": {
            "payg": settings.stripe_price_payg,
            "lite": settings.stripe_price_lite,
            "plus": settings.stripe_price_plus,
        },
    }


@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout(
    body: CheckoutSessionRequest,
    user: DbUser,
    session: SessionDep,
) -> CheckoutSessionResponse:
    _stripe_or_503()
    try:
        result = stripe_svc.create_checkout_session(session, user, plan=body.plan)
    except stripe_svc.StripeNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "stripe_not_configured", "message": str(exc)},
        ) from exc
    except stripe_svc.StripeBillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "checkout_failed", "message": str(exc)},
        ) from exc
    except Exception as exc:
        logger.exception("Checkout Session create failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "stripe_upstream",
                "message": "Could not create Stripe Checkout Session.",
            },
        ) from exc
    return CheckoutSessionResponse(
        checkout_url=result["checkout_url"],
        session_id=result["session_id"],
        plan=body.plan,
    )


@router.post("/portal", response_model=PortalSessionResponse)
def create_portal(user: DbUser, session: SessionDep) -> PortalSessionResponse:
    _stripe_or_503()
    try:
        url = stripe_svc.create_portal_session(session, user)
    except stripe_svc.StripeNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "stripe_not_configured", "message": str(exc)},
        ) from exc
    except Exception as exc:
        logger.exception("Customer Portal Session create failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "stripe_upstream",
                "message": "Could not create Stripe Customer Portal Session.",
            },
        ) from exc
    return PortalSessionResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, str]:
    """Stripe webhook — signature required; no JWT (Stripe calls this)."""
    if not settings.stripe_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured",
        )
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )
    payload = await request.body()
    try:
        event = stripe_svc.construct_webhook_event(
            payload,
            stripe_signature,
            settings=settings,
        )
    except stripe_svc.StripeNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.warning("Stripe webhook verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature or payload",
        ) from exc

    try:
        result = stripe_svc.handle_stripe_event(session, event, settings=settings)
    except credits_svc.InsufficientCreditsError as exc:
        logger.exception("Webhook grant produced negative balance")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credit grant failed",
        ) from exc
    except Exception:
        logger.exception("Stripe webhook handler failed for %s", event.get("id"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook handler failed",
        ) from None

    return {"status": "ok", "result": result}
