from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from services.auth_service import get_db
from models.models import Feedback, User, StudyNote
from schemas.schemas import (
    FeedbackRequest, FeedbackOut,
    CreateStudyNoteRequest, StudyNoteOut,
)
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Feedback & Notes"])


# ── Feedback ───────────────────────────────────────────────────────────────

@router.post("/feedback", response_model=FeedbackOut)
async def submit_feedback(
    req: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Feedback).filter(
        Feedback.user_id == current_user.id,
        Feedback.content_type == req.content_type,
        Feedback.content_id == req.content_id,
    ).first()

    if existing:
        existing.rating = req.rating
        existing.comment = req.comment
        db.commit()
        db.refresh(existing)
        return FeedbackOut(
            id=existing.id,
            user_id=existing.user_id,
            content_type=existing.content_type,
            content_id=existing.content_id,
            rating=existing.rating,
            comment=existing.comment,
            created_at=existing.created_at,
            user_name=current_user.name,
        )

    feedback = Feedback(
        user_id=current_user.id,
        content_type=req.content_type,
        content_id=req.content_id,
        rating=req.rating,
        comment=req.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackOut(
        id=feedback.id,
        user_id=feedback.user_id,
        content_type=feedback.content_type,
        content_id=feedback.content_id,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at,
        user_name=current_user.name,
    )


@router.get("/feedback/{content_type}/{content_id}")
async def get_feedback(
    content_type: str,
    content_id: UUID,
    db: Session = Depends(get_db),
):
    feedbacks = (
        db.query(Feedback, User.name)
        .join(User, User.id == Feedback.user_id)
        .filter(
            Feedback.content_type == content_type,
            Feedback.content_id == content_id,
        )
        .order_by(Feedback.created_at.desc())
        .all()
    )

    avg_rating = (
        db.query(sql_func.avg(Feedback.rating))
        .filter(
            Feedback.content_type == content_type,
            Feedback.content_id == content_id,
        )
        .scalar()
    )

    return {
        "content_type": content_type,
        "content_id": str(content_id),
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0,
        "total_feedbacks": len(feedbacks),
        "feedbacks": [
            {
                "id": str(f.id),
                "user_name": name,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f, name in feedbacks
        ],
    }


# ── Study Notes ────────────────────────────────────────────────────────────

@router.post("/notes", response_model=StudyNoteOut)
async def create_note(
    req: CreateStudyNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = StudyNote(
        user_id=current_user.id,
        title=req.title,
        content=req.content,
        subject=req.subject,
        tags=req.tags,
        group_id=req.group_id,
        is_shared=req.is_shared,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes")
async def list_notes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notes = (
        db.query(StudyNote)
        .filter(StudyNote.user_id == current_user.id)
        .order_by(StudyNote.updated_at.desc())
        .all()
    )
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "subject": n.subject,
            "tags": n.tags,
            "is_shared": n.is_shared,
            "group_id": str(n.group_id) if n.group_id else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        }
        for n in notes
    ]


@router.get("/notes/{note_id}")
async def get_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = db.query(StudyNote).filter(
        StudyNote.id == note_id,
        StudyNote.user_id == current_user.id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "subject": note.subject,
        "tags": note.tags,
        "is_shared": note.is_shared,
        "group_id": str(note.group_id) if note.group_id else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


@router.put("/notes/{note_id}")
async def update_note(
    note_id: UUID,
    req: CreateStudyNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = db.query(StudyNote).filter(
        StudyNote.id == note_id,
        StudyNote.user_id == current_user.id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    note.title = req.title
    note.content = req.content
    note.subject = req.subject
    note.tags = req.tags
    note.is_shared = req.is_shared
    if req.group_id:
        note.group_id = req.group_id

    db.commit()
    db.refresh(note)
    return {"status": "updated", "note_id": str(note.id)}


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = db.query(StudyNote).filter(
        StudyNote.id == note_id,
        StudyNote.user_id == current_user.id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return {"status": "deleted", "note_id": str(note_id)}
