"""Stripe Customer + Checkout + webhook grant handling (direct, not RevenueCat)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import stripe
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.models.user import User
from app.schemas.billing import CheckoutPlan
from app.services import credits as credits_svc
from app.services.credits import (
    apply_wallet_delta,
    ensure_free_grant,
    set_period_allotment,
)

logger = logging.getLogger(__name__)


class StripeNotConfiguredError(RuntimeError):
    pass


class StripeBillingError(RuntimeError):
    pass


def _require_settings(settings: Settings | None = None) -> Settings:
    s = settings or get_settings()
    if not s.stripe_configured:
        raise StripeNotConfiguredError(
            "Stripe is not configured. Set STRIPE_SECRET_KEY "
            "(and webhook/price IDs) in the environment."
        )
    mismatch = s.stripe_mode_mismatch
    if mismatch:
        logger.warning("Stripe mode mismatch: %s", mismatch)
        raise StripeBillingError(mismatch)
    stripe.api_key = s.stripe_secret_key.strip()
    return s


def price_id_for_plan(plan: CheckoutPlan, settings: Settings) -> str:
    mapping = {
        "payg": settings.stripe_price_payg.strip(),
        "lite": settings.stripe_price_lite.strip(),
        "plus": settings.stripe_price_plus.strip(),
    }
    price_id = mapping[plan]
    if not price_id:
        raise StripeBillingError(f"No Stripe price configured for plan={plan}")
    return price_id


def plan_for_price_id(price_id: str, settings: Settings) -> CheckoutPlan | None:
    normalized = price_id.strip()
    if normalized == settings.stripe_price_payg.strip():
        return "payg"
    if normalized == settings.stripe_price_lite.strip():
        return "lite"
    if normalized == settings.stripe_price_plus.strip():
        return "plus"
    return None


def credits_for_plan(plan: CheckoutPlan, settings: Settings) -> int:
    if plan == "payg":
        return max(0, int(settings.stripe_credits_payg))
    if plan == "lite":
        return max(0, int(settings.stripe_credits_lite))
    return max(0, int(settings.stripe_credits_plus))


def _price_id_from_line(line: dict[str, Any]) -> str | None:
    """Extract price id from an invoice/checkout line (API version tolerant)."""
    price = line.get("price")
    if isinstance(price, dict) and price.get("id"):
        return str(price["id"])
    if isinstance(price, str) and price.startswith("price_"):
        return price
    pricing = line.get("pricing")
    if isinstance(pricing, dict):
        details = pricing.get("price_details")
        if isinstance(details, dict) and details.get("price"):
            return str(details["price"])
    plan = line.get("plan")
    if isinstance(plan, dict) and plan.get("id"):
        # Legacy plan id sometimes equals price id for simple products.
        return str(plan["id"])
    return None


def ensure_stripe_customer(
    session: Session,
    user: User,
    *,
    settings: Settings | None = None,
) -> User:
    """Create or reuse a Stripe Customer linked to the app user UUID."""
    s = _require_settings(settings)
    user = ensure_free_grant(session, user, settings=s)
    if user.stripe_customer_id:
        return user

    create_kwargs: dict[str, Any] = {
        "metadata": {"user_id": str(user.id), "app": "updateapply"},
        "name": user.display_name or user.email or str(user.id),
    }
    if user.email:
        create_kwargs["email"] = user.email
    customer = stripe.Customer.create(**create_kwargs)
    user.stripe_customer_id = str(customer.id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_checkout_session(
    session: Session,
    user: User,
    *,
    plan: CheckoutPlan,
    settings: Settings | None = None,
) -> dict[str, str]:
    s = _require_settings(settings)
    user = ensure_stripe_customer(session, user, settings=s)
    customer_id = user.stripe_customer_id
    if not customer_id:
        raise StripeBillingError("Stripe customer missing after ensure")
    price_id = price_id_for_plan(plan, s)
    mode = "payment" if plan == "payg" else "subscription"
    checkout = stripe.checkout.Session.create(
        customer=customer_id,
        mode=mode,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=s.resolved_checkout_success_url(),
        cancel_url=s.resolved_checkout_cancel_url(),
        client_reference_id=str(user.id),
        metadata={
            "user_id": str(user.id),
            "plan": plan,
            "app": "updateapply",
        },
        allow_promotion_codes=True,
    )
    url = checkout.url
    session_id = checkout.id
    if not url or not session_id:
        raise StripeBillingError("Stripe Checkout Session missing url/id")
    return {"checkout_url": str(url), "session_id": str(session_id), "plan": plan}


def create_portal_session(
    session: Session,
    user: User,
    *,
    settings: Settings | None = None,
) -> str:
    s = _require_settings(settings)
    user = ensure_stripe_customer(session, user, settings=s)
    customer_id = user.stripe_customer_id
    if not customer_id:
        raise StripeBillingError("Stripe customer missing after ensure")
    portal = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=s.resolved_portal_return_url(),
    )
    url = portal.url
    if not url:
        raise StripeBillingError("Stripe Customer Portal Session missing url")
    return str(url)


def _user_from_metadata(
    session: Session, metadata: dict[str, Any] | None
) -> User | None:
    if not metadata:
        return None
    raw = metadata.get("user_id")
    if not raw:
        return None
    try:
        user_id = UUID(str(raw))
    except ValueError:
        return None
    return session.get(User, user_id)


def _user_from_customer_id(session: Session, customer_id: str | None) -> User | None:
    if not customer_id:
        return None
    return session.exec(
        select(User).where(User.stripe_customer_id == customer_id)
    ).first()


def _subscription_period_key(
    subscription_id: str | None, period_start: int | None, fallback: str
) -> str:
    """Collapse Checkout + first invoice onto one period grant when possible."""
    if subscription_id and period_start is not None:
        return f"stripe:sub_period:{subscription_id}:{period_start}"
    return fallback


def _period_start_from_lines(lines: list[Any]) -> int | None:
    for line in lines:
        if not isinstance(line, dict):
            continue
        period = line.get("period")
        if isinstance(period, dict) and period.get("start") is not None:
            try:
                return int(period["start"])
            except TypeError, ValueError:
                continue
    return None


def grant_from_checkout_session(
    session: Session,
    checkout_session: dict[str, Any],
    *,
    stripe_event_id: str,
    settings: Settings,
) -> None:
    """Grant credits after Checkout completes (PAYG + first subscription period)."""
    unpaid = checkout_session.get("payment_status") not in {
        "paid",
        "no_payment_required",
    }
    # Subscriptions may still be unpaid on session create; wait for invoice.paid.
    if unpaid and checkout_session.get("mode") == "subscription":
        return
    if unpaid and checkout_session.get("mode") == "payment":
        return

    metadata = checkout_session.get("metadata") or {}
    plan_raw = metadata.get("plan")
    plan: CheckoutPlan | None = None
    if plan_raw in {"payg", "lite", "plus"}:
        plan = plan_raw  # type: ignore[assignment]
    user = _user_from_metadata(session, metadata)
    if user is None:
        user = _user_from_customer_id(session, checkout_session.get("customer"))
    if user is None:
        logger.warning(
            "checkout.session.completed: no user for session %s",
            checkout_session.get("id"),
        )
        return
    if user.stripe_customer_id is None and checkout_session.get("customer"):
        user.stripe_customer_id = str(checkout_session["customer"])
        session.add(user)
        session.commit()
        session.refresh(user)

    if plan is None:
        logger.warning(
            "checkout.session.completed: missing plan metadata for %s",
            checkout_session.get("id"),
        )
        return

    amount = credits_for_plan(plan, settings)
    if amount <= 0:
        return

    session_id = str(checkout_session.get("id") or "")
    if plan == "payg":
        apply_wallet_delta(
            session,
            user_id=user.id,
            delta=amount,
            reason="payg",
            idempotency_key=f"stripe:checkout:{session_id}",
            stripe_event_id=stripe_event_id,
        )
        return

    # Lite/Plus: set period allotment (no rollover). Share key with invoice when
    # subscription id + period start are known.
    subscription_id = checkout_session.get("subscription")
    if isinstance(subscription_id, dict):
        subscription_id = subscription_id.get("id")
    sub_id = str(subscription_id) if subscription_id else None
    period_start: int | None = None
    if sub_id:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            raw_start = getattr(sub, "current_period_start", None)
            if raw_start is not None:
                period_start = int(raw_start)
        except Exception:
            logger.warning(
                "checkout.session.completed: could not load subscription %s",
                sub_id,
                exc_info=True,
            )
    key = _subscription_period_key(
        sub_id, period_start, fallback=f"stripe:checkout:{session_id}"
    )
    set_period_allotment(
        session,
        user_id=user.id,
        allotment=amount,
        plan=plan,  # type: ignore[arg-type]
        reason=f"{plan}_period",
        idempotency_key=key,
        stripe_event_id=stripe_event_id,
    )


def grant_from_invoice_paid(
    session: Session,
    invoice: dict[str, Any],
    *,
    stripe_event_id: str,
    settings: Settings,
) -> None:
    """Grant / reset monthly allowance on subscription invoice payment."""
    customer_id = invoice.get("customer")
    user = _user_from_customer_id(session, customer_id)
    if user is None:
        logger.warning("invoice.paid: no user for customer %s", customer_id)
        return

    lines = (invoice.get("lines") or {}).get("data") or []
    plan: CheckoutPlan | None = None
    for line in lines:
        if not isinstance(line, dict):
            continue
        price_id = _price_id_from_line(line)
        if not price_id:
            continue
        plan = plan_for_price_id(str(price_id), settings)
        if plan in {"lite", "plus"}:
            break
        if plan == "payg":
            # One-time Checkout owns PAYG; ignore invoice noise.
            return

    if plan not in {"lite", "plus"}:
        return

    amount = credits_for_plan(plan, settings)
    if amount <= 0:
        return

    subscription_id = invoice.get("subscription")
    if isinstance(subscription_id, dict):
        subscription_id = subscription_id.get("id")
    sub_id = str(subscription_id) if subscription_id else None
    period_start = _period_start_from_lines(lines)
    invoice_id = str(invoice.get("id") or "")
    key = _subscription_period_key(
        sub_id, period_start, fallback=f"stripe:invoice:{invoice_id}"
    )
    set_period_allotment(
        session,
        user_id=user.id,
        allotment=amount,
        plan=plan,  # type: ignore[arg-type]
        reason=f"{plan}_period",
        idempotency_key=key,
        stripe_event_id=stripe_event_id,
    )


def _apply_subscription_change(
    session: Session,
    subscription: dict[str, Any],
    *,
    stripe_event_id: str,
    settings: Settings,
) -> None:
    """Track plan on create/update; clear period credits when subscription ends."""
    customer_id = subscription.get("customer")
    user = _user_from_customer_id(session, customer_id)
    if user is None:
        logger.warning(
            "subscription change: no user for customer %s",
            customer_id,
        )
        return

    status = str(subscription.get("status") or "")
    sub_id = str(subscription.get("id") or "")
    if status in {"canceled", "unpaid", "incomplete_expired"}:
        credits_svc.clear_subscription_period(
            session,
            user_id=user.id,
            idempotency_key=f"stripe:sub_ended:{sub_id}:{status}:{stripe_event_id}",
            stripe_event_id=stripe_event_id,
        )
        return

    items = (subscription.get("items") or {}).get("data") or []
    plan: CheckoutPlan | None = None
    for item in items:
        if not isinstance(item, dict):
            continue
        price = item.get("price") if isinstance(item.get("price"), dict) else {}
        price_id = price.get("id") if isinstance(price, dict) else None
        if not price_id:
            continue
        plan = plan_for_price_id(str(price_id), settings)
        if plan in {"lite", "plus"}:
            break
    if plan in {"lite", "plus"} and user.billing_plan != plan:
        user.billing_plan = plan
        session.add(user)
        session.commit()


def handle_stripe_event(
    session: Session,
    event: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> str:
    """Dispatch a verified Stripe event. Returns a short status for logs/response."""
    s = settings or get_settings()
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    data_object = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        grant_from_checkout_session(
            session,
            data_object,
            stripe_event_id=event_id,
            settings=s,
        )
        return "checkout_granted"
    if event_type == "invoice.paid":
        grant_from_invoice_paid(
            session,
            data_object,
            stripe_event_id=event_id,
            settings=s,
        )
        return "invoice_granted"
    if event_type in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _apply_subscription_change(
            session,
            data_object,
            stripe_event_id=event_id,
            settings=s,
        )
        return "subscription_synced"
    return f"ignored:{event_type}"


def construct_webhook_event(
    payload: bytes,
    sig_header: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    s = _require_settings(settings)
    secret = s.stripe_webhook_secret.strip()
    if not secret:
        raise StripeNotConfiguredError(
            "STRIPE_WEBHOOK_SECRET is required to verify Stripe webhooks."
        )
    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    # stripe-python returns Event (StripeObject); normalize to a plain dict.
    to_dict = getattr(event, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, dict):
            return raw
    raise StripeBillingError("Unexpected Stripe event payload type")
