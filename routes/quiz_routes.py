from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.auth_service import get_db
from models.models import Quiz, QuizQuestion, QuizAttempt, User, ClassPlan
from schemas.schemas import GenerateQuizRequest, SubmitQuizRequest, QuizOut, QuizAttemptOut
from agent.quiz_agent import generate_quiz, grade_quiz
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz"])


@router.post("/generate", response_model=QuizOut)
async def generate_quiz_endpoint(
    req: GenerateQuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = req.content or ""

    if req.source_type == "class_plan" and req.source_id:
        plan = db.query(ClassPlan).filter(
            ClassPlan.id == req.source_id,
            ClassPlan.user_id == current_user.id,
        ).first()
        if plan:
            content = f"Subject: {plan.subject}\nOutline: {plan.outline}\n"
            if plan.generated_plan:
                content += f"Generated Plan: {plan.generated_plan}"

    quiz_data = generate_quiz(
        topic=req.topic,
        content=content if content else None,
        difficulty=req.difficulty,
        question_count=req.question_count,
        question_types=req.question_types,
    )

    quiz = Quiz(
        user_id=current_user.id,
        title=quiz_data.get("title", f"Quiz: {req.topic}"),
        topic=req.topic,
        description=quiz_data.get("description", ""),
        difficulty=req.difficulty,
        question_count=len(quiz_data.get("questions", [])),
        source_type=req.source_type,
        source_id=req.source_id,
    )
    db.add(quiz)
    db.flush()

    for idx, q in enumerate(quiz_data.get("questions", [])):
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_type=q["question_type"],
            question_text=q["question_text"],
            options=q.get("options"),
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation", ""),
            points=q.get("points", 1),
            order_index=idx,
        )
        db.add(question)

    db.commit()
    db.refresh(quiz)

    return quiz


@router.post("/submit", response_model=QuizAttemptOut)
async def submit_quiz(
    req: SubmitQuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(Quiz.id == req.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()
    questions_data = [
        {
            "id": str(q.id),
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "points": q.points,
        }
        for q in questions
    ]

    result = grade_quiz(questions_data, req.answers)

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        answers=req.answers,
        score=result["score"],
        total_points=result["total_points"],
        earned_points=result["earned_points"],
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return QuizAttemptOut(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        total_points=attempt.total_points,
        earned_points=attempt.earned_points,
        completed_at=attempt.completed_at,
        answers=attempt.answers,
        corrections=result["corrections"],
    )


@router.get("/list")
async def list_quizzes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quizzes = (
        db.query(Quiz)
        .filter(Quiz.user_id == current_user.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(q.id),
            "title": q.title,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "question_count": q.question_count,
            "is_published": q.is_published,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in quizzes
    ]


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.order_index)
        .all()
    )

    return {
        "id": str(quiz.id),
        "title": quiz.title,
        "topic": quiz.topic,
        "description": quiz.description,
        "difficulty": quiz.difficulty,
        "question_count": quiz.question_count,
        "is_published": quiz.is_published,
        "created_at": quiz.created_at.isoformat() if quiz.created_at else None,
        "questions": [
            {
                "id": str(q.id),
                "question_type": q.question_type,
                "question_text": q.question_text,
                "options": q.options,
                "points": q.points,
                "order_index": q.order_index,
            }
            for q in questions
        ],
    }


@router.get("/{quiz_id}/attempts")
async def get_quiz_attempts(
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id,
        )
        .order_by(QuizAttempt.completed_at.desc())
        .all()
    )
    return [
        {
            "id": str(a.id),
            "score": a.score,
            "total_points": a.total_points,
            "earned_points": a.earned_points,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in attempts
    ]


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.user_id == current_user.id,
    ).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    db.delete(quiz)
    db.commit()
    return {"status": "deleted", "quiz_id": str(quiz_id)}
