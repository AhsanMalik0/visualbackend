import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.models import User, ResearchDocument
from schemas.schemas import SaveResearchDocRequest, ResearchDocOut, AIAssistRequest
from services.auth_service import require_auth, get_db

router = APIRouter(prefix="/api/v1/research", tags=["research-docs"])


@router.post("/documents")
async def save_document(
    req: SaveResearchDocRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if req.doc_id:
        doc = db.query(ResearchDocument).filter(
            ResearchDocument.id == req.doc_id,
            ResearchDocument.user_id == user.id,
        ).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        doc.title = req.title
        doc.content = req.content
        doc.template_type = req.template_type
        doc.citation_style = req.citation_style
        doc.references = req.references
    else:
        doc = ResearchDocument(
            user_id=user.id,
            title=req.title,
            content=req.content,
            template_type=req.template_type,
            citation_style=req.citation_style,
            references=req.references,
        )
        db.add(doc)

    db.commit()
    db.refresh(doc)

    return ResearchDocOut(
        id=doc.id,
        title=doc.title,
        content=doc.content,
        template_type=doc.template_type,
        citation_style=doc.citation_style,
        references=doc.references,
        is_public=doc.is_public,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/documents")
async def list_documents(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    docs = db.query(ResearchDocument).filter(
        ResearchDocument.user_id == user.id,
    ).order_by(ResearchDocument.updated_at.desc()).all()

    return [
        ResearchDocOut(
            id=d.id,
            title=d.title,
            content=None,
            template_type=d.template_type,
            citation_style=d.citation_style,
            references=None,
            is_public=d.is_public,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in docs
    ]


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    doc = db.query(ResearchDocument).filter(ResearchDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if str(doc.user_id) != str(user.id) and not doc.is_public:
        raise HTTPException(status_code=403, detail="Access denied")

    return ResearchDocOut(
        id=doc.id,
        title=doc.title,
        content=doc.content,
        template_type=doc.template_type,
        citation_style=doc.citation_style,
        references=doc.references,
        is_public=doc.is_public,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    doc = db.query(ResearchDocument).filter(
        ResearchDocument.id == doc_id,
        ResearchDocument.user_id == user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()
    return {"status": "Document deleted"}


@router.post("/ai-assist")
async def ai_writing_assist(
    req: AIAssistRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    import httpx

    action_prompts = {
        "improve": "Improve the following text for clarity, grammar, and academic quality. Keep the same meaning and tone:\n\n",
        "expand": "Expand the following text with more detail, examples, and supporting arguments while maintaining academic tone:\n\n",
        "simplify": "Simplify the following text to make it easier to understand while keeping the key information:\n\n",
        "rewrite": "Rewrite the following text in a different way while preserving the same meaning and academic quality:\n\n",
    }

    if req.action not in action_prompts:
        raise HTTPException(status_code=400, detail="Invalid action. Use: improve, expand, simplify, rewrite")

    prompt = action_prompts[req.action] + req.text

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    if os.getenv("ANTHROPIC_API_KEY"):
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="AI service error")
        data = response.json()
        result_text = data.get("content", [{}])[0].get("text", "")
    else:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="AI service error")
        data = response.json()
        result_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    return {"result": result_text, "action": req.action}
