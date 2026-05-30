import stripe
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import HTTPException

from utils.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, PLAN_CONFIG, CREDIT_PACKS, FRONTEND_URL
from models.models import User, Payment, Subscription

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(
    user: User,
    price_type: str,  # "subscription" or "credits"
    item_id: str,  # plan name or credit pack id
    billing_period: str = "monthly",  # "monthly" or "yearly"
) -> dict:

    if price_type == "subscription":
        plan = PLAN_CONFIG.get(item_id)
        if not plan or item_id == "free":
            raise HTTPException(status_code=400, detail="Invalid plan")

        price_key = f"stripe_price_{billing_period}"
        stripe_price_id = plan.get(price_key)

        # If no Stripe price ID configured, create a dynamic price
        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"WizAI {plan['name']} Plan",
                    "description": f"{plan['credits_per_month']} credits/month - {', '.join(plan['features'][:3])}",
                },
                "unit_amount": int(plan[f"price_{billing_period}"] * 100) if billing_period == "monthly" else int(plan["price_yearly"] * 100),
                "recurring": {"interval": "month" if billing_period == "monthly" else "year"},
            },
            "quantity": 1,
        }]

        if stripe_price_id:
            line_items = [{"price": stripe_price_id, "quantity": 1}]

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user.email,
            line_items=line_items,
            success_url=f"{FRONTEND_URL}/plans?status=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/plans?status=cancelled",
            metadata={
                "user_id": str(user.id),
                "plan": item_id,
                "billing_period": billing_period,
                "type": "subscription",
            },
        )

    elif price_type == "credits":
        pack = CREDIT_PACKS.get(item_id)
        if not pack:
            raise HTTPException(status_code=400, detail="Invalid credit pack")

        session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=user.email,
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{pack['credits']} WizAI Credits",
                        "description": f"One-time purchase of {pack['credits']} generation credits",
                    },
                    "unit_amount": int(pack["price_usd"] * 100),
                },
                "quantity": 1,
            }],
            success_url=f"{FRONTEND_URL}/plans?status=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/plans?status=cancelled",
            metadata={
                "user_id": str(user.id),
                "pack_id": item_id,
                "credits": str(pack["credits"]),
                "type": "credits",
            },
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid price_type. Use 'subscription' or 'credits'")

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }


def create_card_payment(
    user: User,
    amount_usd: float,
    credits: int,
    db: Session,
) -> dict:

    try:
        # Create a PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=int(amount_usd * 100),
            currency="usd",
            metadata={
                "user_id": str(user.id),
                "credits": str(credits),
                "type": "credits",
            },
            description=f"{credits} WizAI Credits for {user.email}",
            receipt_email=user.email,
        )

        # Store payment record
        payment = Payment(
            user_id=str(user.id),
            type="credits",
            item_id=f"credits_{credits}",
            amount_usd=amount_usd,
            status="pending",
            stripe_payment_id=intent.id,
        )
        db.add(payment)
        db.commit()

        return {
            "client_secret": intent.client_secret,
            "payment_id": intent.id,
            "status": "requires_confirmation",
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e.user_message or e))


def handle_webhook_event(payload: bytes, sig_header: str, db: Session) -> dict:

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)
    elif event_type == "payment_intent.succeeded":
        _handle_payment_succeeded(data, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_cancelled(data, db)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data, db)

    return {"status": "ok", "event_type": event_type}


def _handle_checkout_completed(data: dict, db: Session):
    metadata = data.get("metadata", {})
    user_id = metadata.get("user_id")

    if not user_id:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    payment_type = metadata.get("type")

    if payment_type == "credits":
        credits = int(metadata.get("credits", 0))
        user.credits = (user.credits or 0) + credits

        # Record payment
        payment = Payment(
            user_id=str(user.id),
            type="credits",
            item_id=metadata.get("pack_id", "custom"),
            amount_usd=data.get("amount_total", 0) / 100.0,
            status="confirmed",
            stripe_payment_id=data.get("payment_intent"),
        )
        db.add(payment)

    elif payment_type == "subscription":
        plan = metadata.get("plan", "free")
        plan_config = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])

        user.plan = plan
        user.credits = plan_config["credits_per_month"]

        # Create/update subscription record
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if sub:
            sub.plan = plan
            sub.status = "active"
            sub.stripe_subscription_id = data.get("subscription")
        else:
            sub = Subscription(
                user_id=user.id,
                plan=plan,
                status="active",
                stripe_subscription_id=data.get("subscription"),
                stripe_customer_id=data.get("customer"),
            )
            db.add(sub)

        # Record payment
        payment = Payment(
            user_id=str(user.id),
            type="subscription",
            item_id=plan,
            amount_usd=data.get("amount_total", 0) / 100.0,
            status="confirmed",
            stripe_payment_id=data.get("payment_intent"),
        )
        db.add(payment)

    db.commit()


def _handle_payment_succeeded(data: dict, db: Session):
    payment_id = data.get("id")
    metadata = data.get("metadata", {})
    user_id = metadata.get("user_id")

    if not user_id:
        return

    # Update payment record
    payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_id).first()
    if payment and payment.status != "confirmed":
        payment.status = "confirmed"

        # Add credits
        credits = int(metadata.get("credits", 0))
        if credits > 0:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.credits = (user.credits or 0) + credits

        db.commit()


def _handle_subscription_updated(data: dict, db: Session):
    stripe_sub_id = data.get("id")
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).first()
    if sub:
        sub.status = data.get("status", "active")
        db.commit()


def _handle_subscription_cancelled(data: dict, db: Session):
    stripe_sub_id = data.get("id")
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).first()
    if sub:
        sub.status = "cancelled"
        # Downgrade user to free plan
        user = db.query(User).filter(User.id == sub.user_id).first()
        if user:
            user.plan = "free"
            user.credits = min(user.credits or 0, 10)
        db.commit()


def _handle_invoice_paid(data: dict, db: Session):
    stripe_sub_id = data.get("subscription")
    if not stripe_sub_id:
        return

    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).first()
    if sub and sub.status == "active":
        plan_config = PLAN_CONFIG.get(sub.plan, PLAN_CONFIG["free"])
        user = db.query(User).filter(User.id == sub.user_id).first()
        if user:
            user.credits = plan_config["credits_per_month"]
            db.commit()
