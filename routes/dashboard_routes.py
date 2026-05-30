from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from services.auth_service import get_db
from models.models import (
    User, Visual, Quiz, QuizAttempt, ContentSummary,
    StudyNote, Feedback, Group, GroupMember, ClassPlan,
)
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_visuals = db.query(sql_func.count(Visual.id)).filter(
        Visual.user_id == current_user.id
    ).scalar() or 0

    total_quizzes = db.query(sql_func.count(Quiz.id)).filter(
        Quiz.user_id == current_user.id
    ).scalar() or 0

    total_summaries = db.query(sql_func.count(ContentSummary.id)).filter(
        ContentSummary.user_id == current_user.id
    ).scalar() or 0

    total_notes = db.query(sql_func.count(StudyNote.id)).filter(
        StudyNote.user_id == current_user.id
    ).scalar() or 0

    total_class_plans = db.query(sql_func.count(ClassPlan.id)).filter(
        ClassPlan.user_id == current_user.id
    ).scalar() or 0

    groups_count = db.query(sql_func.count(GroupMember.id)).filter(
        GroupMember.user_id == current_user.id
    ).scalar() or 0

    quiz_attempts = db.query(sql_func.count(QuizAttempt.id)).filter(
        QuizAttempt.user_id == current_user.id
    ).scalar() or 0

    avg_quiz_score = db.query(sql_func.avg(QuizAttempt.score)).filter(
        QuizAttempt.user_id == current_user.id
    ).scalar()

    recent_visuals = (
        db.query(Visual)
        .filter(Visual.user_id == current_user.id)
        .order_by(Visual.created_at.desc())
        .limit(5)
        .all()
    )

    recent_quizzes = (
        db.query(Quiz)
        .filter(Quiz.user_id == current_user.id)
        .order_by(Quiz.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "user": {
            "name": current_user.name,
            "email": current_user.email,
            "plan": current_user.plan,
            "credits": current_user.credits,
            "total_generations": current_user.total_generations or 0,
        },
        "stats": {
            "total_visuals": total_visuals,
            "total_quizzes": total_quizzes,
            "total_summaries": total_summaries,
            "total_notes": total_notes,
            "total_class_plans": total_class_plans,
            "groups_joined": groups_count,
            "quiz_attempts": quiz_attempts,
            "avg_quiz_score": round(float(avg_quiz_score), 1) if avg_quiz_score else 0,
        },
        "recent_activity": {
            "visuals": [
                {
                    "id": str(v.id),
                    "topic": v.topic,
                    "item": v.item,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in recent_visuals
            ],
            "quizzes": [
                {
                    "id": str(q.id),
                    "title": q.title,
                    "topic": q.topic,
                    "difficulty": q.difficulty,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in recent_quizzes
            ],
        },
    }
