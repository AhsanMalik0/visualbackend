from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.models import (
    User, Visual, Quiz, QuizAttempt, ContentSummary, ClassPlan,
    ResearchDocument, ContentView,
)
from schemas.schemas import ContentViewRequest
from services.auth_service import require_auth, get_db

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/my")
async def get_my_analytics(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    lectures_created = db.query(Visual).filter(Visual.user_id == user.id).count()
    quizzes_created = db.query(Quiz).filter(Quiz.user_id == user.id).count()
    papers_written = db.query(ResearchDocument).filter(ResearchDocument.user_id == user.id).count()
    summaries_created = db.query(ContentSummary).filter(ContentSummary.user_id == user.id).count()

    total_views = db.query(func.count(ContentView.id)).filter(ContentView.owner_id == user.id).scalar() or 0

    avg_time = db.query(func.avg(ContentView.time_spent_seconds)).filter(
        ContentView.owner_id == user.id,
    ).scalar() or 0
    avg_time_minutes = round(float(avg_time) / 60, 1) if avg_time else 0

    quiz_attempts = db.query(QuizAttempt).join(Quiz).filter(Quiz.user_id == user.id).all()
    total_quiz_attempts = len(quiz_attempts)
    quiz_completion_rate = 0
    if quizzes_created > 0 and total_quiz_attempts > 0:
        quiz_completion_rate = min(round((total_quiz_attempts / quizzes_created) * 100, 1), 100)

    summary_downloads = summaries_created

    content_stats = []
    visuals = db.query(Visual).filter(Visual.user_id == user.id).order_by(Visual.created_at.desc()).limit(20).all()
    for v in visuals:
        views = db.query(func.count(ContentView.id)).filter(
            ContentView.content_id == v.id,
            ContentView.content_type == "lecture",
        ).scalar() or 0
        avg_t = db.query(func.avg(ContentView.time_spent_seconds)).filter(
            ContentView.content_id == v.id,
        ).scalar() or 0
        content_stats.append({
            "id": str(v.id),
            "title": v.topic or "Untitled",
            "type": v.item or "lecture",
            "views": views,
            "avg_time": round(float(avg_t) / 60, 1) if avg_t else 0,
            "quiz_rate": 0,
            "downloads": 0,
        })

    quizzes = db.query(Quiz).filter(Quiz.user_id == user.id).order_by(Quiz.created_at.desc()).limit(10).all()
    for q in quizzes:
        views = db.query(func.count(ContentView.id)).filter(
            ContentView.content_id == q.id,
            ContentView.content_type == "quiz",
        ).scalar() or 0
        attempts = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == q.id).count()
        content_stats.append({
            "id": str(q.id),
            "title": q.title or "Untitled Quiz",
            "type": "quiz",
            "views": views,
            "avg_time": 0,
            "quiz_rate": min(round((attempts / max(views, 1)) * 100, 1), 100) if views > 0 else 0,
            "downloads": 0,
        })

    content_stats.sort(key=lambda x: x["views"], reverse=True)

    return {
        "overview": {
            "lectures_created": lectures_created,
            "quizzes_created": quizzes_created,
            "papers_written": papers_written,
            "total_views": total_views,
            "avg_time_spent": avg_time_minutes,
            "quiz_completion_rate": quiz_completion_rate,
            "summary_downloads": summary_downloads,
        },
        "content_stats": content_stats,
    }


@router.post("/track-view")
async def track_content_view(
    req: ContentViewRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    owner_id = None
    if req.content_type == "lecture":
        content = db.query(Visual).filter(Visual.id == req.content_id).first()
        owner_id = content.user_id if content else user.id
    elif req.content_type == "quiz":
        content = db.query(Quiz).filter(Quiz.id == req.content_id).first()
        owner_id = content.user_id if content else user.id
    elif req.content_type == "paper":
        content = db.query(ResearchDocument).filter(ResearchDocument.id == req.content_id).first()
        owner_id = content.user_id if content else user.id
    else:
        owner_id = user.id

    view = ContentView(
        content_type=req.content_type,
        content_id=req.content_id,
        owner_id=owner_id,
        viewer_id=user.id,
        time_spent_seconds=req.time_spent_seconds,
    )
    db.add(view)
    db.commit()
    return {"status": "View tracked"}
