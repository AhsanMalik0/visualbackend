# src/routes/studyroom_routes.py  — complete updated backend

import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
from datetime import datetime

from models.models import (
    User, StudyRoom, StudyRoomParticipant, StudyRoomMessage,
    StudyRoomQuiz, StudyRoomQuizAttempt, Connection
)
from schemas.schemas import (
    StudyRoomCreate, StudyRoomOut, StudyRoomMessageCreate,
    StudyRoomQuizCreate, StudyRoomQuizAttemptCreate,
)
from services.auth_service import require_auth, get_db

router = APIRouter(prefix="/api/v1/study-rooms", tags=["study-rooms"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def is_creator_or_co(room, participant):
    return str(room.creator_id) == str(participant.user_id) or participant.is_co_creator


def get_participant(db, room_id, user_id):
    return db.query(StudyRoomParticipant).filter(
        StudyRoomParticipant.room_id == room_id,
        StudyRoomParticipant.user_id == user_id
    ).first()


def is_connected(db, user_a, user_b):
    conn = db.query(Connection).filter(
        or_(
            and_(Connection.requester_id == user_a, Connection.receiver_id == user_b),
            and_(Connection.requester_id == user_b, Connection.receiver_id == user_a),
        ),
        Connection.status == "accepted"
    ).first()
    return conn is not None


# ── List rooms ────────────────────────────────────────────────────────────────
@router.get("")
async def list_rooms(
    subject: Optional[str] = None,
    type: Optional[str] = None,
    q: Optional[str] = None,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    query = db.query(StudyRoom).filter(
        StudyRoom.is_deleted == False,
        or_(
            StudyRoom.privacy == "public",
            StudyRoom.creator_id == user.id,
            # user is a participant in private rooms
            StudyRoom.id.in_(
                db.query(StudyRoomParticipant.room_id).filter(
                    StudyRoomParticipant.user_id == user.id
                )
            )
        )
    )
    if subject and subject != "All":
        query = query.filter(StudyRoom.subject == subject)
    if type and type != "all":
        query = query.filter(StudyRoom.type == type)
    if q:
        query = query.filter(
            or_(StudyRoom.name.ilike(f"%{q}%"), StudyRoom.subject.ilike(f"%{q}%"))
        )

    rooms = query.order_by(StudyRoom.created_at.desc()).all()
    result = []
    for r in rooms:
        pcount = db.query(StudyRoomParticipant).filter(StudyRoomParticipant.room_id == r.id).count()
        result.append({
            "id": str(r.id),
            "name": r.name,
            "type": r.type,
            "subject": r.subject,
            "custom_subject": r.custom_subject,
            "goal": r.goal,
            "agenda": r.agenda,
            "persistence": r.persistence,
            "privacy": r.privacy,
            "session_count": r.session_count or 0,
            "creator_id": str(r.creator_id),
            "participant_count": pcount,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return result


# ── Create room ───────────────────────────────────────────────────────────────
@router.post("")
async def create_room(
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    name       = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Room name required")

    privacy    = body.get("privacy", "public")
    invite_tok = secrets.token_urlsafe(12) if privacy == "private" else None

    room = StudyRoom(
        name           = name,
        type           = body.get("type", "text"),
        subject        = body.get("subject", "Other"),
        custom_subject = body.get("custom_subject", None),
        goal           = body.get("goal", ""),
        agenda         = body.get("agenda", ""),
        persistence    = body.get("persistence", "temporary"),
        privacy        = privacy,
        invite_token   = invite_tok,
        creator_id     = user.id,
        session_count  = 1,
        is_deleted     = False,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    # Auto-join creator as co_creator
    participant = StudyRoomParticipant(
        room_id=room.id, user_id=user.id,
        status="studying", is_co_creator=True
    )
    db.add(participant)
    db.commit()

    return {
        "id": str(room.id),
        "invite_token": invite_tok,
        "message": "Room created"
    }


# ── Get room detail ───────────────────────────────────────────────────────────
@router.get("/{room_id}")
async def get_room(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(
        StudyRoom.id == room_id,
        StudyRoom.is_deleted == False
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    pcount = db.query(StudyRoomParticipant).filter(StudyRoomParticipant.room_id == room_id).count()
    part   = get_participant(db, room_id, user.id)

    return {
        "id": str(room.id),
        "name": room.name,
        "type": room.type,
        "subject": room.subject,
        "custom_subject": room.custom_subject,
        "goal": room.goal,
        "agenda": room.agenda,
        "persistence": room.persistence,
        "privacy": room.privacy,
        "invite_token": room.invite_token if str(room.creator_id) == str(user.id) else None,
        "creator_id": str(room.creator_id),
        "session_count": room.session_count or 0,
        "participant_count": pcount,
        "is_co_creator": part.is_co_creator if part else False,
        "is_creator": str(room.creator_id) == str(user.id),
        "created_at": room.created_at.isoformat() if room.created_at else None,
    }


# ── Join room ─────────────────────────────────────────────────────────────────
@router.post("/{room_id}/join")
async def join_room(
    room_id: str,
    body: dict = {},
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(
        StudyRoom.id == room_id,
        StudyRoom.is_deleted == False
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Private room: must be connected to creator OR have invite token
    if room.privacy == "private" and str(room.creator_id) != str(user.id):
        invite_token = body.get("invite_token", "")
        connected    = is_connected(db, user.id, room.creator_id)
        if not connected and invite_token != room.invite_token:
            raise HTTPException(status_code=403, detail="Access denied. You need an invite link or must be connected to the creator.")

    existing = get_participant(db, room_id, user.id)
    if not existing:
        p = StudyRoomParticipant(
            room_id=room_id, user_id=user.id, status="studying", is_co_creator=False
        )
        db.add(p)
        db.commit()

    return {"status": "joined"}


# ── Join via invite token ─────────────────────────────────────────────────────
@router.post("/join-by-token/{token}")
async def join_by_token(
    token: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(
        StudyRoom.invite_token == token,
        StudyRoom.is_deleted == False
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Invalid invite link")

    existing = get_participant(db, room.id, user.id)
    if not existing:
        p = StudyRoomParticipant(
            room_id=room.id, user_id=user.id, status="studying", is_co_creator=False
        )
        db.add(p)
        db.commit()

    return {"room_id": str(room.id), "status": "joined"}


# ── Leave room ────────────────────────────────────────────────────────────────
@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    p = get_participant(db, room_id, user.id)
    if p:
        db.delete(p)
        db.commit()

    # Auto-delete temporary rooms when creator leaves and no one remains
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if room and room.persistence == "temporary" and str(room.creator_id) == str(user.id):
        remaining = db.query(StudyRoomParticipant).filter(StudyRoomParticipant.room_id == room_id).count()
        if remaining == 0:
            room.is_deleted = True
            db.commit()

    return {"status": "left"}


# ── Delete room (creator only, cascades for everyone) ─────────────────────────
@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    part = get_participant(db, room_id, user.id)
    if str(room.creator_id) != str(user.id) and not (part and part.is_co_creator):
        raise HTTPException(status_code=403, detail="Only creator or co-creator can delete room")

    room.is_deleted = True
    db.commit()
    return {"status": "deleted"}


# ── Update session (start new session, increment counter, set goal+agenda) ────
@router.post("/{room_id}/start-session")
async def start_session(
    room_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    part = get_participant(db, room_id, user.id)
    if str(room.creator_id) != str(user.id) and not (part and part.is_co_creator):
        raise HTTPException(status_code=403, detail="Only creator or co-creator can start session")

    room.goal          = body.get("goal", room.goal)
    room.agenda        = body.get("agenda", room.agenda)
    room.session_count = (room.session_count or 0) + 1
    db.commit()

    return {"session_count": room.session_count, "status": "session started"}


# ── Get participants ──────────────────────────────────────────────────────────
@router.get("/{room_id}/participants")
async def get_participants(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    parts = db.query(StudyRoomParticipant).filter(StudyRoomParticipant.room_id == room_id).all()
    result = []
    for p in parts:
        u = db.query(User).filter(User.id == p.user_id).first()
        if u:
            result.append({
                "user_id":      str(p.user_id),
                "name":         u.name,
                "email":        u.email,
                "status":       p.status,
                "goal":         p.goal,
                "is_co_creator":p.is_co_creator,
                "joined_at":    p.joined_at.isoformat() if p.joined_at else None,
            })
    return result


# ── Update my status ──────────────────────────────────────────────────────────
@router.patch("/{room_id}/status")
async def update_status(
    room_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    p = get_participant(db, room_id, user.id)
    if p:
        p.status = body.get("status", p.status)
        db.commit()
    return {"status": "updated"}


# ── Update my goal ────────────────────────────────────────────────────────────
@router.patch("/{room_id}/goal")
async def update_goal(
    room_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    p = get_participant(db, room_id, user.id)
    if p:
        p.goal = body.get("goal", p.goal)
        db.commit()
    return {"status": "updated"}


# ── Assign co-creator ─────────────────────────────────────────────────────────
@router.post("/{room_id}/co-creator/{target_user_id}")
async def assign_co_creator(
    room_id: str,
    target_user_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    my_part = get_participant(db, room_id, user.id)
    if str(room.creator_id) != str(user.id) and not (my_part and my_part.is_co_creator):
        raise HTTPException(status_code=403, detail="Only creator or co-creator can assign co-creators")

    target = get_participant(db, room_id, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target user not in room")

    target.is_co_creator = True
    db.commit()
    return {"status": "co-creator assigned"}


# ── Revoke co-creator ─────────────────────────────────────────────────────────
@router.delete("/{room_id}/co-creator/{target_user_id}")
async def revoke_co_creator(
    room_id: str,
    target_user_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room or str(room.creator_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Only the creator can revoke co-creator status")

    target = get_participant(db, room_id, target_user_id)
    if target:
        target.is_co_creator = False
        db.commit()
    return {"status": "co-creator revoked"}


# ── Messages ──────────────────────────────────────────────────────────────────
@router.get("/{room_id}/messages")
async def get_messages(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    msgs = db.query(StudyRoomMessage).filter(
        StudyRoomMessage.room_id == room_id
    ).order_by(StudyRoomMessage.created_at).all()

    result = []
    cache = {}
    for m in msgs:
        sid = str(m.sender_id)
        if sid not in cache:
            u = db.query(User).filter(User.id == m.sender_id).first()
            cache[sid] = u.name if u else "Unknown"
        result.append({
            "id":          str(m.id),
            "sender_id":   sid,
            "sender_name": cache[sid],
            "content":     m.content,
            "type":        getattr(m, "type", "text"),
            "created_at":  m.created_at.isoformat() if m.created_at else None,
        })
    return result


@router.post("/{room_id}/messages")
async def send_message(
    room_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content required")

    msg_type = body.get("type", "text")

    # Enforce type rules: text-only rooms can't send voice
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if room and room.type == "text" and msg_type == "voice":
        raise HTTPException(status_code=400, detail="Voice not allowed in text-only rooms")

    msg = StudyRoomMessage(
        room_id=room_id, sender_id=user.id,
        content=content
    )
    # If model has type column:
    if hasattr(msg, "type"):
        msg.type = msg_type

    db.add(msg)
    db.commit()
    db.refresh(msg)

    u = db.query(User).filter(User.id == user.id).first()
    return {
        "id":          str(msg.id),
        "sender_id":   str(user.id),
        "sender_name": u.name if u else "Unknown",
        "content":     content,
        "type":        msg_type,
        "created_at":  msg.created_at.isoformat() if msg.created_at else None,
    }


# ── Shared notes ──────────────────────────────────────────────────────────────
@router.get("/{room_id}/notes")
async def get_notes(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"notes": getattr(room, "notes", "") or ""}


@router.patch("/{room_id}/notes")
async def update_notes(
    room_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if hasattr(room, "notes"):
        room.notes = body.get("notes", "")
        db.commit()
    return {"status": "updated"}


# ── QUIZ ──────────────────────────────────────────────────────────────────────
@router.post("/{room_id}/quiz")
async def create_quiz(
    room_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    part = get_participant(db, room_id, user.id)
    if not is_creator_or_co(room, part):
        raise HTTPException(status_code=403, detail="Only creator or co-creator can create quiz")

    quiz = StudyRoomQuiz(
        room_id    = room_id,
        creator_id = user.id,
        title      = body.get("title", "Quiz"),
        questions  = body.get("questions", []),
        time_limit = body.get("time_limit", 300),
        is_active  = True,
        result_shared = False,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    # Broadcast system message
    msg = StudyRoomMessage(
        room_id=room_id, sender_id=user.id,
        content=f"📋 A quiz has been shared: {quiz.title}"
    )
    if hasattr(msg, "type"):
        msg.type = "system"
    db.add(msg); db.commit()

    return {"id": str(quiz.id), "status": "quiz created"}


@router.get("/{room_id}/quiz/active")
async def get_active_quiz(
    room_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    quiz = db.query(StudyRoomQuiz).filter(
        StudyRoomQuiz.room_id == room_id,
        StudyRoomQuiz.is_active == True
    ).order_by(StudyRoomQuiz.created_at.desc()).first()

    if not quiz:
        return None

    # Check if user already attempted
    attempted = db.query(StudyRoomQuizAttempt).filter(
        StudyRoomQuizAttempt.quiz_id == quiz.id,
        StudyRoomQuizAttempt.user_id == user.id
    ).first()

    # Total time = time_limit + extended_by
    total_time = quiz.time_limit + (quiz.extended_by or 0)

    return {
        "id":            str(quiz.id),
        "title":         quiz.title,
        "questions":     quiz.questions,
        "time_limit":    total_time,
        "is_active":     quiz.is_active,
        "result_shared": quiz.result_shared,
        "already_attempted": attempted is not None,
        "created_at":    quiz.created_at.isoformat() if quiz.created_at else None,
    }


@router.post("/{room_id}/quiz/{quiz_id}/attempt")
async def submit_quiz_attempt(
    room_id: str,
    quiz_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    quiz = db.query(StudyRoomQuiz).filter(
        StudyRoomQuiz.id == quiz_id,
        StudyRoomQuiz.is_active == True
    ).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found or expired")

    existing = db.query(StudyRoomQuizAttempt).filter(
        StudyRoomQuizAttempt.quiz_id == quiz_id,
        StudyRoomQuizAttempt.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already attempted")

    answers = body.get("answers", {})
    score   = 0
    for i, q in enumerate(quiz.questions):
        if str(answers.get(str(i))) == str(q.get("answer")):
            score += 1

    attempt = StudyRoomQuizAttempt(
        quiz_id=quiz_id, user_id=user.id,
        answers=answers, score=score
    )
    db.add(attempt); db.commit()

    return {"score": score, "total": len(quiz.questions)}


@router.patch("/{room_id}/quiz/{quiz_id}/extend")
async def extend_quiz_time(
    room_id: str,
    quiz_id: str,
    body: dict,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    part = get_participant(db, room_id, user.id)
    if not is_creator_or_co(room, part):
        raise HTTPException(status_code=403, detail="Only creator or co-creator can extend time")

    quiz = db.query(StudyRoomQuiz).filter(StudyRoomQuiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    extra = body.get("extra_seconds", 60)
    quiz.extended_by = (quiz.extended_by or 0) + extra
    db.commit()

    # Broadcast
    msg = StudyRoomMessage(
        room_id=room_id, sender_id=user.id,
        content=f"⏱ Quiz time extended by {extra//60}m {extra%60}s"
    )
    if hasattr(msg, "type"):
        msg.type = "system"
    db.add(msg); db.commit()

    return {"extended_by": quiz.extended_by}


@router.patch("/{room_id}/quiz/{quiz_id}/share-results")
async def share_quiz_results(
    room_id: str,
    quiz_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    part = get_participant(db, room_id, user.id)
    if not is_creator_or_co(room, part):
        raise HTTPException(status_code=403, detail="Only creator or co-creator can share results")

    quiz = db.query(StudyRoomQuiz).filter(StudyRoomQuiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    quiz.result_shared = True
    db.commit()

    # Fetch all attempts
    attempts = db.query(StudyRoomQuizAttempt).filter(
        StudyRoomQuizAttempt.quiz_id == quiz_id
    ).order_by(StudyRoomQuizAttempt.score.desc()).all()

    results = []
    for a in attempts:
        u = db.query(User).filter(User.id == a.user_id).first()
        results.append({
            "user_id":   str(a.user_id),
            "name":      u.name if u else "Unknown",
            "score":     a.score,
            "total":     len(quiz.questions),
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
        })

    # Broadcast
    msg = StudyRoomMessage(
        room_id=room_id, sender_id=user.id,
        content=f"📊 Quiz results shared: {quiz.title}"
    )
    if hasattr(msg, "type"):
        msg.type = "system"
    db.add(msg); db.commit()

    return {"results": results}


@router.get("/{room_id}/quiz/{quiz_id}/results")
async def get_quiz_results(
    room_id: str,
    quiz_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    quiz = db.query(StudyRoomQuiz).filter(StudyRoomQuiz.id == quiz_id).first()
    if not quiz or not quiz.result_shared:
        raise HTTPException(status_code=403, detail="Results not shared yet")

    attempts = db.query(StudyRoomQuizAttempt).filter(
        StudyRoomQuizAttempt.quiz_id == quiz_id
    ).order_by(StudyRoomQuizAttempt.score.desc()).all()

    results = []
    for a in attempts:
        u = db.query(User).filter(User.id == a.user_id).first()
        results.append({
            "user_id": str(a.user_id),
            "name":    u.name if u else "Unknown",
            "score":   a.score,
            "total":   len(quiz.questions),
        })
    return {"quiz_title": quiz.title, "results": results}


@router.patch("/{room_id}/quiz/{quiz_id}/close")
async def close_quiz(
    room_id: str,
    quiz_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    part = get_participant(db, room_id, user.id)
    if not is_creator_or_co(room, part):
        raise HTTPException(status_code=403, detail="Only creator or co-creator can close quiz")

    quiz = db.query(StudyRoomQuiz).filter(StudyRoomQuiz.id == quiz_id).first()
    if quiz:
        quiz.is_active = False
        db.commit()
    return {"status": "quiz closed"}