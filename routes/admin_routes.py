from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, extract, cast, Date
from typing import Optional
from datetime import datetime, timedelta, timezone

from services.auth_service import get_db, require_auth
from models.models import (
    User, Visual, Payment, Subscription, APIUsageLog,
    UserReview, APIServiceConfig, Quiz, ContentSummary, ClassPlan,
)
from schemas.schemas import ReviewModerationRequest, ToggleServiceRequest

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin role."""
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── GET /admin/dashboard ────────────────────────────────────────────────────
@router.get("/dashboard")
async def admin_dashboard(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    total_users = db.query(sql_func.count(User.id)).scalar()
    new_users_30d = db.query(sql_func.count(User.id)).filter(User.created_at >= thirty_days_ago).scalar()
    new_users_7d = db.query(sql_func.count(User.id)).filter(User.created_at >= seven_days_ago).scalar()

    total_visuals = db.query(sql_func.count(Visual.id)).scalar()
    visuals_30d = db.query(sql_func.count(Visual.id)).filter(Visual.created_at >= thirty_days_ago).scalar()

    total_revenue = db.query(sql_func.sum(Payment.amount_usd)).filter(Payment.status == "confirmed").scalar()
    revenue_30d = (
        db.query(sql_func.sum(Payment.amount_usd))
        .filter(Payment.status == "confirmed", Payment.created_at >= thirty_days_ago)
        .scalar()
    )

    active_subscriptions = db.query(sql_func.count(Subscription.id)).filter(Subscription.status == "active").scalar()

    # Plan distribution
    plan_dist = (
        db.query(User.plan, sql_func.count(User.id))
        .group_by(User.plan)
        .all()
    )

    return {
        "users": {
            "total": total_users or 0,
            "new_30d": new_users_30d or 0,
            "new_7d": new_users_7d or 0,
        },
        "visualizations": {
            "total": total_visuals or 0,
            "last_30d": visuals_30d or 0,
        },
        "revenue": {
            "total_usd": round(total_revenue or 0, 2),
            "last_30d_usd": round(revenue_30d or 0, 2),
        },
        "subscriptions": {
            "active": active_subscriptions or 0,
            "plan_distribution": {plan: count for plan, count in plan_dist} if plan_dist else {},
        },
    }


# ── GET /admin/users ────────────────────────────────────────────────────────
@router.get("/users")
async def admin_list_users(
    page: int = 1,
    limit: int = 50,
    plan: Optional[str] = None,
    search: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)

    if plan:
        query = query.filter(User.plan == plan)
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "plan": u.plan,
                "credits": u.credits,
                "role": u.role,
                "total_generations": u.total_generations or 0,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_generation_at": u.last_generation_at.isoformat() if u.last_generation_at else None,
            }
            for u in users
        ],
    }


# ── GET /admin/revenue ──────────────────────────────────────────────────────
@router.get("/revenue")
async def admin_revenue(
    days: int = 30,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    payments = (
        db.query(Payment)
        .filter(Payment.status == "confirmed", Payment.created_at >= since)
        .order_by(Payment.created_at.desc())
        .all()
    )

    total = sum(p.amount_usd for p in payments)
    subscription_revenue = sum(p.amount_usd for p in payments if p.type == "subscription")
    credit_revenue = sum(p.amount_usd for p in payments if p.type == "credits")

    return {
        "period_days": days,
        "total_revenue_usd": round(total, 2),
        "subscription_revenue_usd": round(subscription_revenue, 2),
        "credit_revenue_usd": round(credit_revenue, 2),
        "transaction_count": len(payments),
        "recent_transactions": [
            {
                "id": str(p.id),
                "user_id": str(p.user_id),
                "type": p.type,
                "item_id": p.item_id,
                "amount_usd": p.amount_usd,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments[:20]
        ],
    }


# ── PATCH /admin/users/{user_id}/plan ───────────────────────────────────────
@router.patch("/users/{user_id}/plan")
async def admin_update_user_plan(
    user_id: str,
    plan: str,
    credits: Optional[int] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from utils.config import PLAN_CONFIG

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if plan not in PLAN_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {list(PLAN_CONFIG.keys())}")

    user.plan = plan
    if credits is not None:
        user.credits = credits
    else:
        user.credits = PLAN_CONFIG[plan]["credits_per_month"]

    db.add(user)
    db.commit()

    return {"status": "updated", "user_id": str(user.id), "plan": plan, "credits": user.credits}


# ══════════════════════════════════════════════════════════════════════════
# FINANCIAL ANALYTICS
# ══════════════════════════════════════════════════════════════════════════

@router.get("/financials")
async def admin_financials(
    days: int = 365,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    payments = (
        db.query(Payment)
        .filter(Payment.status == "confirmed", Payment.created_at >= since)
        .order_by(Payment.created_at.asc())
        .all()
    )

    stripe_volume = sum(p.amount_usd for p in payments if p.stripe_payment_id)
    crypto_volume = sum(p.amount_usd for p in payments if p.nowpay_id)
    total_volume = stripe_volume + crypto_volume

    monthly_data = {}
    for p in payments:
        if p.created_at:
            month_key = p.created_at.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {"month": month_key, "stripe": 0.0, "crypto": 0.0, "total": 0.0}
            if p.stripe_payment_id:
                monthly_data[month_key]["stripe"] += p.amount_usd
            elif p.nowpay_id:
                monthly_data[month_key]["crypto"] += p.amount_usd
            monthly_data[month_key]["total"] += p.amount_usd

    monthly_trend = sorted(monthly_data.values(), key=lambda x: x["month"])

    crypto_payments = [p for p in payments if p.nowpay_id]
    token_dist = {}
    for p in crypto_payments:
        token = p.item_id.upper() if p.item_id else "OTHER"
        token_dist[token] = token_dist.get(token, 0) + p.amount_usd

    recent_txns = sorted(payments, key=lambda p: p.created_at or datetime.min, reverse=True)[:20]

    return {
        "summary": {
            "total_volume_usd": round(total_volume, 2),
            "stripe_volume_usd": round(stripe_volume, 2),
            "crypto_volume_usd": round(crypto_volume, 2),
            "transaction_count": len(payments),
        },
        "monthly_trend": [
            {k: round(v, 2) if isinstance(v, float) else v for k, v in m.items()}
            for m in monthly_trend
        ],
        "token_distribution": {k: round(v, 2) for k, v in token_dist.items()},
        "recent_transactions": [
            {
                "id": str(p.id),
                "user_id": str(p.user_id),
                "type": p.type,
                "item_id": p.item_id,
                "amount_usd": p.amount_usd,
                "channel": "stripe" if p.stripe_payment_id else "crypto" if p.nowpay_id else "other",
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in recent_txns
        ],
    }


# ══════════════════════════════════════════════════════════════════════════
# API & GATEWAY CONTROLLER
# ══════════════════════════════════════════════════════════════════════════

@router.get("/apis")
async def admin_list_apis(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    services = db.query(APIServiceConfig).order_by(APIServiceConfig.category, APIServiceConfig.service_name).all()

    if not services:
        defaults = [
            ("stripe", "Stripe Payments", "payment"),
            ("nowpayments", "NOWPayments Crypto", "payment"),
            ("gemini", "Google Gemini AI", "ai"),
            ("kimi", "Kimi AI (Moonshot)", "ai"),
        ]
        for sname, dname, cat in defaults:
            svc = APIServiceConfig(service_name=sname, display_name=dname, is_active=True, category=cat)
            db.add(svc)
        db.commit()
        services = db.query(APIServiceConfig).order_by(APIServiceConfig.category, APIServiceConfig.service_name).all()

    return {
        "services": [
            {
                "id": str(s.id),
                "service_name": s.service_name,
                "display_name": s.display_name,
                "is_active": s.is_active,
                "category": s.category,
                "last_toggled_at": s.last_toggled_at.isoformat() if s.last_toggled_at else None,
            }
            for s in services
        ],
    }


@router.patch("/apis/{service_name}")
async def admin_toggle_api(
    service_name: str,
    req: ToggleServiceRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle an API service on/off (circuit breaker)."""
    service = db.query(APIServiceConfig).filter(APIServiceConfig.service_name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    service.is_active = req.is_active
    service.last_toggled_by = admin.id
    service.last_toggled_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "updated",
        "service_name": service.service_name,
        "is_active": service.is_active,
    }


@router.get("/apis/status")
async def get_api_status(db: Session = Depends(get_db)):
    """Public endpoint: get active/inactive status of payment/AI services."""
    services = db.query(APIServiceConfig).all()
    return {s.service_name: s.is_active for s in services}


# ══════════════════════════════════════════════════════════════════════════
# SERVICE USAGE MONITORING
# ══════════════════════════════════════════════════════════════════════════

@router.get("/services")
async def admin_service_usage(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_visuals = db.query(sql_func.count(Visual.id)).scalar() or 0
    total_lectures = db.query(sql_func.count(Visual.id)).filter(Visual.item == "Lecture").scalar() or 0
    total_ppts = db.query(sql_func.count(Visual.id)).filter(Visual.item == "PPT").scalar() or 0
    total_3d = db.query(sql_func.count(Visual.id)).filter(Visual.generation_type == "3d_visual").scalar() or 0
    total_4d = db.query(sql_func.count(Visual.id)).filter(Visual.generation_type == "4d_animation").scalar() or 0
    total_quizzes = db.query(sql_func.count(Quiz.id)).scalar() or 0
    total_summaries = db.query(sql_func.count(ContentSummary.id)).scalar() or 0
    total_class_plans = db.query(sql_func.count(ClassPlan.id)).scalar() or 0

    features = [
        {"name": "3D Visualizations", "key": "3d_visuals", "count": total_3d},
        {"name": "4D Animations", "key": "4d_animations", "count": total_4d},
        {"name": "Lectures Generated", "key": "lectures", "count": total_lectures},
        {"name": "Presentations (PPT)", "key": "presentations", "count": total_ppts},
        {"name": "Quizzes Generated", "key": "quizzes", "count": total_quizzes},
        {"name": "Content Summaries", "key": "summaries", "count": total_summaries},
        {"name": "Class Plans", "key": "class_plans", "count": total_class_plans},
        {"name": "Total Visualizations", "key": "total_visuals", "count": total_visuals},
    ]

    features.sort(key=lambda f: f["count"], reverse=True)

    top_feature = features[0] if features else None

    return {
        "features": features,
        "top_feature": top_feature,
        "total_generations": total_visuals,
    }


# ══════════════════════════════════════════════════════════════════════════
# REVIEW MODERATION CENTER
# ══════════════════════════════════════════════════════════════════════════

@router.get("/reviews")
async def admin_list_reviews(
    status_filter: Optional[str] = "pending",
    page: int = 1,
    limit: int = 50,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List reviews for moderation."""
    query = (
        db.query(UserReview, User.name, User.email)
        .join(User, User.id == UserReview.user_id)
    )

    if status_filter:
        query = query.filter(UserReview.status == status_filter)

    total = query.count()
    reviews = (
        query.order_by(UserReview.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "reviews": [
            {
                "id": str(r.id),
                "user_id": str(r.user_id),
                "user_name": name,
                "user_email": email,
                "rating": r.rating,
                "review_text": r.review_text,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r, name, email in reviews
        ],
    }


@router.patch("/reviews/{review_id}")
async def admin_moderate_review(
    review_id: str,
    req: ReviewModerationRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve or archive a review."""
    review = db.query(UserReview).filter(UserReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if req.action == "approve":
        review.status = "approved"
    elif req.action == "archive":
        review.status = "archived"
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'archive'")

    review.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "updated",
        "review_id": str(review.id),
        "new_status": review.status,
    }
