from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from services.auth_service import get_db, require_auth
from services.payment_service import create_checkout_session, create_card_payment, handle_webhook_event
from models.models import User, Payment
from utils.config import PLAN_CONFIG, CREDIT_PACKS, STRIPE_PUBLISHABLE_KEY

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Request Schemas ─────────────────────────────────────────────────────────
class CheckoutRequest(BaseModel):
    price_type: str  # "subscription" or "credits"
    item_id: str  # plan name or credit pack id
    billing_period: Optional[str] = "monthly"


class CardPaymentRequest(BaseModel):
    user_id: UUID
    credits: int
    amount_usd: float
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None
    card_name: Optional[str] = None


# ── GET /payments/plans ─────────────────────────────────────────────────────
@router.get("/plans")
async def get_plans():
    return {
        "plans": {
            k: {
                "name": v["name"],
                "credits_per_month": v["credits_per_month"],
                "price_monthly": v["price_monthly"],
                "price_yearly": v["price_yearly"],
                "features": v["features"],
                "batch_generation": v["batch_generation"],
                "api_access": v["api_access"],
                "priority_queue": v["priority_queue"],
                "hd_quality": v["hd_quality"],
            }
            for k, v in PLAN_CONFIG.items()
        },
        "credit_packs": CREDIT_PACKS,
        "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY,
    }


# ── POST /payments/checkout ─────────────────────────────────────────────────
@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    user: User = Depends(require_auth),
):
    result = create_checkout_session(
        user=user,
        price_type=req.price_type,
        item_id=req.item_id,
        billing_period=req.billing_period,
    )
    return result


# ── POST /payments/card ─────────────────────────────────────────────────────
@router.post("/card")
async def card_payment(
    req: CardPaymentRequest,
    db: Session = Depends(get_db),
):

    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.credits < 10:
        raise HTTPException(status_code=400, detail="Minimum purchase is 10 credits")

    if req.amount_usd < 1.0:
        raise HTTPException(status_code=400, detail="Minimum amount is $1.00")

    result = create_card_payment(
        user=user,
        amount_usd=req.amount_usd,
        credits=req.credits,
        db=db,
    )
    return result


# ── POST /payments/webhook ──────────────────────────────────────────────────
@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    result = handle_webhook_event(payload, sig_header, db)
    return result


# ── GET /payments/transactions/{user_id} ────────────────────────────────────
@router.get("/transactions/{user_id}")
async def get_transactions(user_id: UUID, db: Session = Depends(get_db)):
    """Get payment transaction history for a user."""
    payments = (
        db.query(Payment)
        .filter(Payment.user_id == str(user_id))
        .order_by(Payment.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": str(p.id),
            "type": p.type,
            "item_id": p.item_id,
            "amount_usd": p.amount_usd,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]


# ── GET /payments/subscription/{user_id} ───────────────────────────────────
@router.get("/subscription/{user_id}")
async def get_subscription(user_id: UUID, db: Session = Depends(get_db)):
    from models.models import Subscription

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()

    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])

    return {
        "user_id": str(user.id),
        "plan": user.plan,
        "plan_name": plan_config["name"],
        "credits": user.credits or 0,
        "credits_per_month": plan_config["credits_per_month"],
        "status": sub.status if sub else "active",
        "features": plan_config["features"],
        "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
    }
