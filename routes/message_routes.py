from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from models.models import User, DirectMessage, Connection
from schemas.schemas import SendDirectMessageRequest, DirectMessageOut, ConversationOut
from services.auth_service import require_auth, get_db

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])


@router.get("/conversations")
async def get_conversations(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    messages = db.query(DirectMessage).filter(
        or_(DirectMessage.sender_id == user.id, DirectMessage.receiver_id == user.id),
    ).order_by(desc(DirectMessage.created_at)).all()

    seen = set()
    convos = []
    for m in messages:
        other_id = m.receiver_id if m.sender_id == user.id else m.sender_id
        if str(other_id) in seen:
            continue
        seen.add(str(other_id))

        other_user = db.query(User).filter(User.id == other_id).first()
        if not other_user:
            continue

        convos.append(ConversationOut(
            user_id=other_id,
            name=other_user.name,
            email=other_user.email,
            last_message=m.content[:100] if m.content else None,
            last_message_at=m.created_at,
            unread_count=0,
        ))

    return convos


@router.get("/{other_user_id}")
async def get_messages(
    other_user_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    messages = db.query(DirectMessage).filter(
        or_(
            and_(DirectMessage.sender_id == user.id, DirectMessage.receiver_id == other_user_id),
            and_(DirectMessage.sender_id == other_user_id, DirectMessage.receiver_id == user.id),
        )
    ).order_by(DirectMessage.created_at).all()

    result = []
    sender_cache = {}
    for m in messages:
        sid = str(m.sender_id)
        if sid not in sender_cache:
            s = db.query(User).filter(User.id == m.sender_id).first()
            sender_cache[sid] = s.name if s else "Unknown"

        result.append(DirectMessageOut(
            id=m.id,
            sender_id=m.sender_id,
            receiver_id=m.receiver_id,
            sender_name=sender_cache[sid],
            content=m.content,
            created_at=m.created_at,
        ))

    return result


@router.post("/send")
async def send_message(
    req: SendDirectMessageRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if str(req.receiver_id) == str(user.id):
        raise HTTPException(status_code=400, detail="Cannot message yourself")

    receiver = db.query(User).filter(User.id == req.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    conn = db.query(Connection).filter(
        or_(
            and_(Connection.requester_id == user.id, Connection.receiver_id == req.receiver_id),
            and_(Connection.requester_id == req.receiver_id, Connection.receiver_id == user.id),
        ),
        Connection.status == "accepted",
    ).first()

    if not conn:
        raise HTTPException(status_code=403, detail="You must be connected to message this user")

    msg = DirectMessage(
        sender_id=user.id,
        receiver_id=req.receiver_id,
        content=req.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return DirectMessageOut(
        id=msg.id,
        sender_id=msg.sender_id,
        receiver_id=msg.receiver_id,
        sender_name=user.name,
        content=msg.content,
        created_at=msg.created_at,
    )
