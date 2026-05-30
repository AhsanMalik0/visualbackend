from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.auth_service import get_db
# from database import SessionLocal
from models.models import ContentSummary, User
from schemas.schemas import SummarizeRequest, SummaryOut, CustomizeLectureRequest
from agent.summarize_agent import summarize_content, customize_lecture
from services.auth_service import get_current_user


router = APIRouter(prefix="/api/v1/summarize", tags=["Summarization"])

# async def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

@router.post("/", response_model=SummaryOut)
async def summarize(
    req: SummarizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = summarize_content(
        title=req.title,
        content=req.content,
        summary_type=req.summary_type,
        language=req.language,
    )

    summary = ContentSummary(
        user_id=current_user.id,
        title=req.title,
        original_content=req.content,
        summary=result["summary"],
        summary_type=req.summary_type,
        key_points=result.get("key_points"),
        word_count_original=result.get("word_count_original"),
        word_count_summary=result.get("word_count_summary"),
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    return summary


@router.get("/history")
async def get_summaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summaries = (
        db.query(ContentSummary)
        .filter(ContentSummary.user_id == current_user.id)
        .order_by(ContentSummary.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "summary_type": s.summary_type,
            "word_count_original": s.word_count_original,
            "word_count_summary": s.word_count_summary,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in summaries
    ]


@router.get("/{summary_id}")
async def get_summary(
    summary_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = db.query(ContentSummary).filter(
        ContentSummary.id == summary_id,
        ContentSummary.user_id == current_user.id,
    ).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    return {
        "id": str(summary.id),
        "title": summary.title,
        "original_content": summary.original_content,
        "summary": summary.summary,
        "summary_type": summary.summary_type,
        "key_points": summary.key_points,
        "word_count_original": summary.word_count_original,
        "word_count_summary": summary.word_count_summary,
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
    }


@router.delete("/{summary_id}")
async def delete_summary(
    summary_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = db.query(ContentSummary).filter(
        ContentSummary.id == summary_id,
        ContentSummary.user_id == current_user.id,
    ).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    db.delete(summary)
    db.commit()
    return {"status": "deleted", "summary_id": str(summary_id)}


@router.post("/customize-lecture")
async def customize_lecture_endpoint(
    req: CustomizeLectureRequest,
    current_user: User = Depends(get_current_user),
):
    result = customize_lecture(
        topic=req.topic,
        content=req.content,
        customization_type=req.customization_type,
        target_audience=req.target_audience,
        language=req.language,
        additional_instructions=req.additional_instructions,
    )
    return result
