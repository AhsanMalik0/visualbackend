from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from database import SessionLocal
from models.models import (
    Group, GroupMember, GroupPost, GroupPostLike, GroupPostComment, User
)

router = APIRouter(prefix="/api/v1/groups", tags=["Group Feed"])


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CreatePostRequest(BaseModel):
    group_id: str
    author_id: str
    content_type: str
    content_id: Optional[str] = None
    text: Optional[str] = None
    title: Optional[str] = None
    is_restricted: bool = False


class CommentRequest(BaseModel):
    user_id: str
    text: str


class LikeRequest(BaseModel):
    user_id: str


class SearchGroupsRequest(BaseModel):
    query: Optional[str] = None
    subject: Optional[str] = None


class JoinGroupRequest(BaseModel):
    user_id: str
    group_id: str


class CreateGroupRequest(BaseModel):
    created_by: str
    name: str
    description: Optional[str] = ""
    privacy: str = "private"
    subject: Optional[str] = None


def _check_membership(db: Session, group_id: str, user_id: str):
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    creator = db.query(Group).filter(
        Group.id == group_id,
        Group.created_by == user_id
    ).first()
    return member is not None or creator is not None


@router.get("/search")
def search_public_groups(q: str = "", subject: str = "", db: Session = Depends(get_db)):
    query = db.query(Group).filter(Group.privacy == "public")
    if q:
        query = query.filter(Group.name.ilike(f"%{q}%"))
    if subject:
        query = query.filter(Group.subject.ilike(f"%{subject}%"))
    groups = query.order_by(Group.created_at.desc()).limit(50).all()
    results = []
    for g in groups:
        creator = db.query(User).filter(User.id == g.created_by).first()
        member_count = db.query(GroupMember).filter(GroupMember.group_id == g.id).count() + 1
        results.append({
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "privacy": g.privacy or "private",
            "subject": g.subject,
            "created_by": str(g.created_by),
            "creator_name": creator.name if creator else "Unknown",
            "member_count": member_count,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })
    return results


@router.post("/join")
def join_public_group(req: JoinGroupRequest, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == req.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.privacy != "public":
        raise HTTPException(status_code=403, detail="This group is private. You need an invite to join.")
    if _check_membership(db, req.group_id, req.user_id):
        raise HTTPException(status_code=400, detail="Already a member")
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    member = GroupMember(group_id=req.group_id, user_id=req.user_id, email=user.email)
    db.add(member)
    db.commit()
    return {"status": "joined", "group_id": str(group.id)}


@router.post("/feed/post")
def create_post(req: CreatePostRequest, db: Session = Depends(get_db)):
    if not _check_membership(db, req.group_id, req.author_id):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    post = GroupPost(
        group_id=req.group_id,
        author_id=req.author_id,
        content_type=req.content_type,
        content_id=req.content_id if req.content_id else None,
        text=req.text,
        title=req.title,
        is_restricted=req.is_restricted,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": str(post.id), "status": "posted"}


@router.get("/feed/{group_id}")
def get_feed(group_id: str, user_id: str = "", db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    is_member = _check_membership(db, group_id, user_id) if user_id else False
    if group.privacy == "private" and not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this private group")
    posts = db.query(GroupPost).filter(
        GroupPost.group_id == group_id
    ).order_by(GroupPost.created_at.desc()).limit(100).all()
    result = []
    for p in posts:
        author = db.query(User).filter(User.id == p.author_id).first()
        like_count = db.query(GroupPostLike).filter(GroupPostLike.post_id == p.id).count()
        user_liked = False
        if user_id:
            user_liked = db.query(GroupPostLike).filter(
                GroupPostLike.post_id == p.id, GroupPostLike.user_id == user_id
            ).first() is not None
        comments = db.query(GroupPostComment).filter(
            GroupPostComment.post_id == p.id
        ).order_by(GroupPostComment.created_at.asc()).all()
        comment_list = []
        for c in comments:
            commenter = db.query(User).filter(User.id == c.user_id).first()
            comment_list.append({
                "id": str(c.id),
                "user_id": str(c.user_id),
                "user_name": commenter.name if commenter else "Unknown",
                "text": c.text,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })
        result.append({
            "id": str(p.id),
            "author_id": str(p.author_id),
            "author_name": author.name if author else "Unknown",
            "content_type": p.content_type,
            "content_id": str(p.content_id) if p.content_id else None,
            "text": p.text,
            "title": p.title,
            "is_restricted": p.is_restricted,
            "like_count": like_count,
            "user_liked": user_liked,
            "comments": comment_list,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return result


@router.post("/feed/{post_id}/like")
def toggle_like(post_id: str, req: LikeRequest, db: Session = Depends(get_db)):
    post = db.query(GroupPost).filter(GroupPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    existing = db.query(GroupPostLike).filter(
        GroupPostLike.post_id == post_id, GroupPostLike.user_id == req.user_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"status": "unliked"}
    like = GroupPostLike(post_id=post_id, user_id=req.user_id)
    db.add(like)
    db.commit()
    return {"status": "liked"}


@router.post("/feed/{post_id}/comment")
def add_comment(post_id: str, req: CommentRequest, db: Session = Depends(get_db)):
    post = db.query(GroupPost).filter(GroupPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Comment text required")
    comment = GroupPostComment(post_id=post_id, user_id=req.user_id, text=req.text.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    user = db.query(User).filter(User.id == req.user_id).first()
    return {
        "id": str(comment.id),
        "user_id": str(comment.user_id),
        "user_name": user.name if user else "Unknown",
        "text": comment.text,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }
