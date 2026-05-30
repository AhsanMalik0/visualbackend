from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.models import User, StudyRoom, StudyRoomParticipant, StudyRoomMessage
from schemas.schemas import (
    CreateStudyRoomRequest, StudyRoomOut, StudyRoomMessageOut, SendRoomMessageRequest, UpdateStatusRequest,
    UpdateGoalRequest, UpdateNotesRequest
)
from services.auth_service import require_auth, get_db

router = APIRouter(prefix="/api/v1/study-rooms", tags=["study-rooms"])

# ── Helpers ───────────────────────────────────────────────────────────────────
def build_room_out(r, db, creator=None, p_count=None):
    if creator is None:
        creator = db.query(User).filter(User.id == r.created_by).first()
    if p_count is None:
        p_count = db.query(StudyRoomParticipant).filter(
            StudyRoomParticipant.room_id == r.id
        ).count()
    return {
        "id":               str(r.id),
        "name":             r.name,
        "description":      r.description,
        "type":             r.room_type,
        "room_type":        r.room_type,
        "persistence":      "persistent" if r.is_persistent else "temporary",
        "is_persistent":    r.is_persistent,
        "subject":          r.subject or "Other",
        "goal":             r.goal,
        "created_by":       str(r.created_by),
        "creator_name":     creator.name if creator else None,
        "group_id":         str(r.group_id) if r.group_id else None,
        "is_active":        r.is_active,
        "participant_count": p_count,
        "created_at":       r.created_at.isoformat() if r.created_at else None,
    }

# ── LIST rooms ────────────────────────────────────────────────────────────────
@router.get("")
async def list_rooms(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    rooms = (
        db.query(StudyRoom)
        .filter(StudyRoom.is_active == True)
        .order_by(StudyRoom.created_at.desc())
        .all()
    )
    return [build_room_out(r, db) for r in rooms]


# ── CREATE room ───────────────────────────────────────────────────────────────
@router.post("")
async def create_room(
    req: CreateStudyRoomRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = StudyRoom(
        name          = req.name,
        description   = getattr(req, "description", None),
        room_type     = req.room_type if hasattr(req, "room_type") else getattr(req, "type", "text"),
        is_persistent = req.is_persistent if hasattr(req, "is_persistent") else (getattr(req, "persistence", "temporary") == "persistent"),
        created_by    = user.id,
        group_id      = getattr(req, "group_id", None) or None,
        subject       = getattr(req, "subject", "Other"),
        goal          = getattr(req, "goal", None),
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    participant = StudyRoomParticipant(room_id=room.id, user_id=user.id, status="studying")
    db.add(participant)
    db.commit()

    return build_room_out(room, db, creator=user, p_count=1)

# ── GET room detail ───────────────────────────────────────────────────────────
@router.get("/{room_id}")
async def get_room(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(
        StudyRoom.id == room_id, StudyRoom.is_active == True
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return build_room_out(room, db)


# ── JOIN room ─────────────────────────────────────────────────────────────────
@router.post("/{room_id}/join")
async def join_room(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(
        StudyRoom.id == room_id, StudyRoom.is_active == True
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    existing = db.query(StudyRoomParticipant).filter(
        StudyRoomParticipant.room_id == room_id,
        StudyRoomParticipant.user_id == user.id,
    ).first()

    if not existing:
        db.add(StudyRoomParticipant(room_id=room.id, user_id=user.id, status="studying"))
        db.commit()

    return {"status": "joined", **build_room_out(room, db)}


# ── LEAVE room ────────────────────────────────────────────────────────────────
@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    participant = db.query(StudyRoomParticipant).filter(
        StudyRoomParticipant.room_id == room_id,
        StudyRoomParticipant.user_id == user.id,
    ).first()
    if participant:
        db.delete(participant)
        db.commit()

    # Deactivate if creator leaves a non-persistent room
    if str(room.created_by) == str(user.id) and not room.is_persistent:
        remaining = db.query(StudyRoomParticipant).filter(
            StudyRoomParticipant.room_id == room_id
        ).count()
        if remaining == 0:
            room.is_active = False
            db.commit()

    return {"status": "left"}

# ── GET participants ──────────────────────────────────────────────────────────
@router.get("/{room_id}/participants")
async def get_participants(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    parts = db.query(StudyRoomParticipant).filter(
        StudyRoomParticipant.room_id == room_id
    ).all()

    result = []
    for p in parts:
        u = db.query(User).filter(User.id == p.user_id).first()
        if u:
            result.append({
                "user_id":   str(p.user_id),
                "name":      u.name,
                "username":  u.email.split("@")[0],
                "status":    p.status or "studying",
                "goal":      p.goal,
                "joined_at": p.joined_at.isoformat() if p.joined_at else None,
            })
    return result

# ── UPDATE status ─────────────────────────────────────────────────────────────
@router.patch("/{room_id}/status")
async def update_status(
    room_id: str,
    req: UpdateStatusRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if req.status not in ("studying", "break", "done"):
        raise HTTPException(status_code=400, detail="Invalid status")

    participant = db.query(StudyRoomParticipant).filter(
        StudyRoomParticipant.room_id == room_id,
        StudyRoomParticipant.user_id == user.id,
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Not in this room")

    participant.status = req.status
    db.commit()
    return {"status": req.status}

# ── UPDATE goal ───────────────────────────────────────────────────────────────
@router.patch("/{room_id}/goal")
async def update_goal(
    room_id: str,
    req: UpdateGoalRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    participant = db.query(StudyRoomParticipant).filter(
        StudyRoomParticipant.room_id == room_id,
        StudyRoomParticipant.user_id == user.id,
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Not in this room")

    participant.goal = req.goal

    # Also update room goal if creator
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if room and str(room.created_by) == str(user.id):
        room.goal = req.goal

    db.commit()
    return {"goal": req.goal}

# ── GET notes ─────────────────────────────────────────────────────────────────
@router.get("/{room_id}/notes")
async def get_notes(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"notes": room.notes or ""}

# ── UPDATE notes ──────────────────────────────────────────────────────────────
@router.patch("/{room_id}/notes")
async def update_notes(
    room_id: str,
    req: UpdateNotesRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verify user is a participant
    participant = db.query(StudyRoomParticipant).filter(
        StudyRoomParticipant.room_id == room_id,
        StudyRoomParticipant.user_id == user.id,
    ).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Must be in the room to edit notes")

    room.notes = req.notes
    db.commit()
    return {"notes": room.notes}


# ── GET messages ──────────────────────────────────────────────────────────────
@router.get("/{room_id}/messages")
async def get_messages(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = (
        db.query(StudyRoomMessage)
        .filter(StudyRoomMessage.room_id == room_id)
        .order_by(StudyRoomMessage.created_at)
        .all()
    )

    sender_cache = {}
    result = []
    for m in messages:
        sid = str(m.sender_id)
        if sid not in sender_cache:
            s = db.query(User).filter(User.id == m.sender_id).first()
            sender_cache[sid] = s.name if s else "Unknown"
        result.append({
            "id":          str(m.id),
            "room_id":     str(m.room_id),
            "sender_id":   str(m.sender_id),
            "sender_name": sender_cache[sid],
            "content":     m.content,
            "created_at":  m.created_at.isoformat() if m.created_at else None,
        })
    return result


 # ── SEND message ──────────────────────────────────────────────────────────────
@router.post("/{room_id}/messages")
async def send_message(
    room_id: str,
    req: SendRoomMessageRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(
        StudyRoom.id == room_id, StudyRoom.is_active == True
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found or inactive")

    msg = StudyRoomMessage(
        room_id=room.id, sender_id=user.id, content=req.content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "id":          str(msg.id),
        "room_id":     str(msg.room_id),
        "sender_id":   str(msg.sender_id),
        "sender_name": user.name,
        "content":     msg.content,
        "created_at":  msg.created_at.isoformat() if msg.created_at else None,
    }