from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from services.auth_service import get_db, require_auth
from models.models import User, UserReview
from schemas.schemas import SubmitReviewRequest, ReviewOut

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.post("/submit", response_model=ReviewOut)
async def submit_review(
    req: SubmitReviewRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    existing = db.query(UserReview).filter(
        UserReview.user_id == user.id,
        UserReview.status != "archived",
    ).first()

    if existing:
        existing.rating = req.rating
        existing.review_text = req.review_text
        existing.status = "pending"
        db.commit()
        db.refresh(existing)
        return ReviewOut(
            id=existing.id,
            user_id=existing.user_id,
            rating=existing.rating,
            review_text=existing.review_text,
            status=existing.status,
            created_at=existing.created_at,
            user_name=user.name,
            user_email=user.email,
        )

    review = UserReview(
        user_id=user.id,
        rating=req.rating,
        review_text=req.review_text,
        status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return ReviewOut(
        id=review.id,
        user_id=review.user_id,
        rating=review.rating,
        review_text=review.review_text,
        status=review.status,
        created_at=review.created_at,
        user_name=user.name,
        user_email=user.email,
    )


@router.get("/approved")
async def get_approved_reviews(db: Session = Depends(get_db)):
    reviews = (
        db.query(UserReview, User.name, User.email)
        .join(User, User.id == UserReview.user_id)
        .filter(UserReview.status == "approved")
        .order_by(UserReview.created_at.desc())
        .limit(50)
        .all()
    )

    avg_rating = (
        db.query(sql_func.avg(UserReview.rating))
        .filter(UserReview.status == "approved")
        .scalar()
    )

    return {
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0,
        "total_reviews": len(reviews),
        "reviews": [
            {
                "id": str(r.id),
                "rating": r.rating,
                "review_text": r.review_text,
                "user_name": name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r, name, email in reviews
        ],
    }


@router.get("/my-review")
async def get_my_review(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    review = db.query(UserReview).filter(
        UserReview.user_id == user.id,
        UserReview.status != "archived",
    ).first()

    if not review:
        return {"has_review": False}

    return {
        "has_review": True,
        "review": {
            "id": str(review.id),
            "rating": review.rating,
            "review_text": review.review_text,
            "status": review.status,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        },
    }
