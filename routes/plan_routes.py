from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone

from services.auth_service import get_db, require_auth
from models.models import User, SubscriptionPlan
from schemas.schemas import (
    CreatePlanRequest, UpdatePlanRequest, PlanOut, FEATURE_KEYS,
)

router = APIRouter(prefix="/admin/plans", tags=["Admin Plans"])


def require_admin(user: User = Depends(require_auth)) -> User:
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _plan_to_dict(p: SubscriptionPlan) -> dict:
    return {
        "id": str(p.id),
        "plan_key": p.plan_key,
        "name": p.name,
        "description": p.description,
        "price_monthly": p.price_monthly or 0,
        "price_yearly": p.price_yearly or 0,
        "credits_per_month": p.credits_per_month or 0,
        "is_active": p.is_active,
        "sort_order": p.sort_order or 0,
        "is_popular": p.is_popular or False,
        "feature_lectures": p.feature_lectures,
        "feature_quiz": p.feature_quiz,
        "feature_summarize": p.feature_summarize,
        "feature_research": p.feature_research,
        "feature_groups": p.feature_groups,
        "feature_connections": p.feature_connections,
        "feature_messaging": p.feature_messaging,
        "feature_study_rooms": p.feature_study_rooms,
        "feature_analytics": p.feature_analytics,
        "feature_3d_visuals": p.feature_3d_visuals,
        "feature_4d_animations": p.feature_4d_animations,
        "feature_ppt": p.feature_ppt,
        "feature_content_library": p.feature_content_library,
        "feature_collaboration": p.feature_collaboration,
        "feature_api_access": p.feature_api_access,
        "feature_batch_generation": p.feature_batch_generation,
        "feature_hd_quality": p.feature_hd_quality,
        "feature_priority_queue": p.feature_priority_queue,
        "max_exports_per_day": p.max_exports_per_day or 1,
        "rate_limit": p.rate_limit or "10/hour",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _seed_defaults(db: Session):
    defaults = [
        {
            "plan_key": "free", "name": "Free", "description": "Get started with basic features",
            "price_monthly": 0, "price_yearly": 0, "credits_per_month": 10,
            "sort_order": 0, "is_popular": False,
            "feature_lectures": True, "feature_quiz": True, "feature_summarize": True,
            "feature_research": False, "feature_groups": False, "feature_connections": False,
            "feature_messaging": False, "feature_study_rooms": False, "feature_analytics": False,
            "feature_3d_visuals": True, "feature_4d_animations": False, "feature_ppt": True,
            "feature_content_library": True, "feature_collaboration": False,
            "feature_api_access": False, "feature_batch_generation": False,
            "feature_hd_quality": False, "feature_priority_queue": False,
            "max_exports_per_day": 1, "rate_limit": "10/hour",
        },
        {
            "plan_key": "starter", "name": "Starter", "description": "For individual creators",
            "price_monthly": 19, "price_yearly": 190, "credits_per_month": 100,
            "sort_order": 1, "is_popular": False,
            "feature_lectures": True, "feature_quiz": True, "feature_summarize": True,
            "feature_research": True, "feature_groups": True, "feature_connections": True,
            "feature_messaging": True, "feature_study_rooms": False, "feature_analytics": False,
            "feature_3d_visuals": True, "feature_4d_animations": False, "feature_ppt": True,
            "feature_content_library": True, "feature_collaboration": False,
            "feature_api_access": False, "feature_batch_generation": False,
            "feature_hd_quality": True, "feature_priority_queue": False,
            "max_exports_per_day": -1, "rate_limit": "60/hour",
        },
        {
            "plan_key": "pro", "name": "Pro", "description": "For power users and teams",
            "price_monthly": 49, "price_yearly": 490, "credits_per_month": 500,
            "sort_order": 2, "is_popular": True,
            "feature_lectures": True, "feature_quiz": True, "feature_summarize": True,
            "feature_research": True, "feature_groups": True, "feature_connections": True,
            "feature_messaging": True, "feature_study_rooms": True, "feature_analytics": True,
            "feature_3d_visuals": True, "feature_4d_animations": True, "feature_ppt": True,
            "feature_content_library": True, "feature_collaboration": True,
            "feature_api_access": True, "feature_batch_generation": True,
            "feature_hd_quality": True, "feature_priority_queue": True,
            "max_exports_per_day": -1, "rate_limit": "200/hour",
        },
        {
            "plan_key": "business", "name": "Business", "description": "For organizations",
            "price_monthly": 149, "price_yearly": 1490, "credits_per_month": 2000,
            "sort_order": 3, "is_popular": False,
            "feature_lectures": True, "feature_quiz": True, "feature_summarize": True,
            "feature_research": True, "feature_groups": True, "feature_connections": True,
            "feature_messaging": True, "feature_study_rooms": True, "feature_analytics": True,
            "feature_3d_visuals": True, "feature_4d_animations": True, "feature_ppt": True,
            "feature_content_library": True, "feature_collaboration": True,
            "feature_api_access": True, "feature_batch_generation": True,
            "feature_hd_quality": True, "feature_priority_queue": True,
            "max_exports_per_day": -1, "rate_limit": "1000/hour",
        },
    ]
    for d in defaults:
        plan = SubscriptionPlan(**d)
        db.add(plan)
    db.commit()


# ── GET /admin/plans ─ List all plans (admin) ─────────────────────────────
@router.get("")
async def list_plans(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.sort_order).all()
    if not plans:
        _seed_defaults(db)
        plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.sort_order).all()
    return {"plans": [_plan_to_dict(p) for p in plans]}


# ── POST /admin/plans ─ Create a new plan ─────────────────────────────────
@router.post("")
async def create_plan(
    req: CreatePlanRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_key == req.plan_key
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Plan '{req.plan_key}' already exists")

    plan = SubscriptionPlan(**req.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"status": "created", "plan": _plan_to_dict(plan)}


# ── PATCH /admin/plans/{plan_key} ─ Update a plan ────────────────────────
@router.patch("/{plan_key}")
async def update_plan(
    plan_key: str,
    req: UpdatePlanRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_key == plan_key
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_key}' not found")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(plan)
    return {"status": "updated", "plan": _plan_to_dict(plan)}


# ── DELETE /admin/plans/{plan_key} ─ Delete a plan ───────────────────────
@router.delete("/{plan_key}")
async def delete_plan(
    plan_key: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if plan_key == "free":
        raise HTTPException(status_code=400, detail="Cannot delete the free plan")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_key == plan_key
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_key}' not found")

    users_on_plan = db.query(User).filter(User.plan == plan_key).count()
    if users_on_plan > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete plan with {users_on_plan} active users. Reassign them first.",
        )

    db.delete(plan)
    db.commit()
    return {"status": "deleted", "plan_key": plan_key}


# ── PATCH /admin/plans/{plan_key}/assign/{user_id} ─ Assign user to plan ─
@router.patch("/{plan_key}/assign/{user_id}")
async def assign_user_plan(
    plan_key: str,
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_key == plan_key
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_key}' not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.plan = plan_key
    user.credits = plan.credits_per_month
    db.commit()
    return {
        "status": "assigned",
        "user_id": str(user.id),
        "plan": plan_key,
        "credits": user.credits,
    }


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS (for users)
# ══════════════════════════════════════════════════════════════════════════

public_router = APIRouter(prefix="/api/v1/plans", tags=["Plans"])


# ── GET /api/v1/plans ─ List active plans (public) ───────────────────────
@public_router.get("")
async def get_available_plans(db: Session = Depends(get_db)):
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.sort_order)
        .all()
    )
    if not plans:
        _seed_defaults(db)
        plans = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.is_active == True)
            .order_by(SubscriptionPlan.sort_order)
            .all()
        )
    return {"plans": [_plan_to_dict(p) for p in plans]}


# ── GET /api/v1/plans/my-features ─ Get current user's feature flags ─────
@public_router.get("/my-features")
async def get_my_features(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_key == (user.plan or "free")
    ).first()

    if not plan:
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_key == "free"
        ).first()

    if not plan:
        return {
            "plan_key": user.plan or "free",
            "plan_name": "Free",
            "features": {k: (k in ("feature_lectures", "feature_quiz", "feature_summarize", "feature_3d_visuals", "feature_ppt", "feature_content_library")) for k in FEATURE_KEYS},
        }

    features = {k: getattr(plan, k, False) for k in FEATURE_KEYS}
    return {
        "plan_key": plan.plan_key,
        "plan_name": plan.name,
        "features": features,
        "credits_per_month": plan.credits_per_month,
        "max_exports_per_day": plan.max_exports_per_day,
    }
