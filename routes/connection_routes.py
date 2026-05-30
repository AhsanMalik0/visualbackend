from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from models.models import User, UserProfile, Connection
from schemas.schemas import (
    ConnectionRequestSchema, ConnectionRespondRequest, ConnectionOut,
    UpdateProfileRequest, UserProfileOut,
)
from services.auth_service import require_auth, get_db

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


@router.get("")
async def get_connections(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    conns = db.query(Connection).filter(
        or_(Connection.requester_id == user.id, Connection.receiver_id == user.id),
        Connection.status == "accepted",
    ).all()

    result = []
    for c in conns:
        other_id = c.receiver_id if c.requester_id == user.id else c.requester_id
        other_user = db.query(User).filter(User.id == other_id).first()
        if not other_user:
            continue
        profile = db.query(UserProfile).filter(UserProfile.user_id == other_id).first()
        result.append(ConnectionOut(
            id=c.id,
            user_id=other_id,
            name=other_user.name,
            email=other_user.email,
            designation=profile.designation if profile else None,
            bio=profile.bio if profile else None,
            interests=profile.interests if profile else None,
            status=c.status,
            created_at=c.created_at,
        ))
    return result


@router.get("/requests")
async def get_pending_requests(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    pending = db.query(Connection).filter(
        Connection.receiver_id == user.id,
        Connection.status == "pending",
    ).all()

    result = []
    for c in pending:
        requester = db.query(User).filter(User.id == c.requester_id).first()
        if not requester:
            continue
        profile = db.query(UserProfile).filter(UserProfile.user_id == c.requester_id).first()
        result.append(ConnectionOut(
            id=c.id,
            user_id=c.requester_id,
            name=requester.name,
            email=requester.email,
            designation=profile.designation if profile else None,
            bio=profile.bio if profile else None,
            interests=profile.interests if profile else None,
            status=c.status,
            created_at=c.created_at,
        ))
    return result


@router.post("/request")
async def send_connection_request(
    req: ConnectionRequestSchema,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if str(req.receiver_id) == str(user.id):
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")

    receiver = db.query(User).filter(User.id == req.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Connection).filter(
        or_(
            and_(Connection.requester_id == user.id, Connection.receiver_id == req.receiver_id),
            and_(Connection.requester_id == req.receiver_id, Connection.receiver_id == user.id),
        )
    ).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="Already connected")
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="Request already pending")
        if existing.status == "rejected":
            existing.status = "pending"
            existing.requester_id = user.id
            existing.receiver_id = req.receiver_id
            db.commit()
            return {"status": "Request re-sent"}

    conn = Connection(requester_id=user.id, receiver_id=req.receiver_id, status="pending")
    db.add(conn)
    db.commit()
    return {"status": "Request sent"}


@router.post("/respond")
async def respond_to_connection(
    req: ConnectionRespondRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    conn = db.query(Connection).filter(
        Connection.id == req.connection_id,
        Connection.receiver_id == user.id,
        Connection.status == "pending",
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="Connection request not found")

    if req.action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'")

    conn.status = "accepted" if req.action == "accept" else "rejected"
    db.commit()
    return {"status": f"Connection {req.action}ed"}


@router.get("/suggested")
async def get_suggested_connections(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    my_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    my_interests = my_profile.interests if my_profile and my_profile.interests else []

    existing_ids = set()
    existing_conns = db.query(Connection).filter(
        or_(Connection.requester_id == user.id, Connection.receiver_id == user.id),
        Connection.status.in_(["accepted", "pending"]),
    ).all()
    for c in existing_conns:
        existing_ids.add(str(c.requester_id))
        existing_ids.add(str(c.receiver_id))
    existing_ids.add(str(user.id))

    all_users = db.query(User).filter(User.id.notin_([u for u in existing_ids if u])).limit(20).all()

    result = []
    for u in all_users:
        if str(u.id) in existing_ids:
            continue
        profile = db.query(UserProfile).filter(UserProfile.user_id == u.id).first()
        user_interests = profile.interests if profile and profile.interests else []
        shared = len(set(my_interests) & set(user_interests)) if my_interests and user_interests else 0
        result.append({
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "designation": profile.designation if profile else None,
            "bio": profile.bio if profile else None,
            "interests": user_interests,
            "shared_interests": shared,
        })

    result.sort(key=lambda x: x["shared_interests"], reverse=True)
    return result[:10]


@router.get("/search")
async def search_users(
    q: str = "",
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if not q or len(q) < 2:
        return []

    users = db.query(User).filter(
        User.id != user.id,
        or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")),
    ).limit(20).all()

    result = []
    for u in users:
        profile = db.query(UserProfile).filter(UserProfile.user_id == u.id).first()
        conn = db.query(Connection).filter(
            or_(
                and_(Connection.requester_id == user.id, Connection.receiver_id == u.id),
                and_(Connection.requester_id == u.id, Connection.receiver_id == user.id),
            )
        ).first()
        result.append({
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "designation": profile.designation if profile else None,
            "bio": profile.bio if profile else None,
            "interests": profile.interests if profile and profile.interests else [],
            "connection_status": conn.status if conn else None,
        })
    return result


# ── Profile endpoints ────────────────────────────────────────────────────

@router.get("/profile/{user_id}")
async def get_user_profile(
    user_id: str,
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    conn_count = db.query(Connection).filter(
        or_(Connection.requester_id == user_id, Connection.receiver_id == user_id),
        Connection.status == "accepted",
    ).count()

    return UserProfileOut(
        user_id=target.id,
        name=target.name,
        email=target.email,
        designation=profile.designation if profile else None,
        bio=profile.bio if profile else None,
        profile_photo=profile.profile_photo if profile else None,
        achievements=profile.achievements if profile else None,
        interests=profile.interests if profile else None,
        connection_count=conn_count,
        created_at=target.created_at,
    )


@router.put("/profile")
async def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    if req.designation is not None:
        profile.designation = req.designation
    if req.bio is not None:
        profile.bio = req.bio
    if req.profile_photo is not None:
        profile.profile_photo = req.profile_photo
    if req.achievements is not None:
        profile.achievements = req.achievements
    if req.interests is not None:
        profile.interests = req.interests

    db.commit()
    db.refresh(profile)
    return {"status": "Profile updated"}
