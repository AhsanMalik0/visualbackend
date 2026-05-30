from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import UUID
import uuid
from fastapi_mail import MessageSchema

from database import SessionLocal
from agent.agents import build_plan_prompt, generate, split_slides_with_ai, edit_prompt, split_slides_prompt, ppt_prompt, plan_generate, visualization_prompt
from utils.utils import create_and_upload_html, sign_url
from models.models import User, Visual, Payment, ClassPlan, Group, GroupMember, GroupMessage, GroupShare
from schemas.schemas import (
    UserCreate, UserLogin, UserOut, LoginResponse, GoogleAuthRequest, AuthResponse,
    Visual_In, Visual_Out, OTPRequest, SavePlanRequest, CreateGroupRequest,
    AddMemberRequest, ShareContentRequest, CreatePaymentRequest, SplitSlidesRequest,
    ProfileResponse, UpdateNameRequest, ChangePasswordRequest, GeneratePlanRequest,
    SendMessageRequest, PLAN_CREDITS, PACK_CREDITS,
)
from botocore.exceptions import ClientError
from utils.config import fm, NOWPAYMENTS_API_KEY, NOWPAYMENTS_IPN_SECRET, NOWPAYMENTS_BASE
from utils.g_oauth import verify_google_user
from services.auth_service import hash_password, verify_password, create_access_token, create_refresh_token
import hmac
import hashlib
import json
import re
import httpx

router = APIRouter()


# Dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── POST /login ─────────────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        return LoginResponse(success=False, message="User Not Found")

    if not verify_password(user_credentials.password, user.password or ""):
        return LoginResponse(success=False, message="Password Incorrect")

    # Generate JWT tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Migrate plaintext password to bcrypt hash on successful login
    if user.password and not (user.password.startswith("$2b$") or user.password.startswith("$2a$")):
        user.password = hash_password(user_credentials.password)
        db.add(user)
        db.commit()

    return LoginResponse(
        success=True,
        user_id=user.id,
        email=user.email,
        access_token=access_token,
        token_type="bearer",
        message="Login Successful",
    )


# ── POST /auth/refresh ──────────────────────────────────────────────────────
@router.post("/auth/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    from services.auth_service import decode_token

    body = await request.json()
    refresh_token_str = body.get("refresh_token")
    if not refresh_token_str:
        raise HTTPException(status_code=400, detail="refresh_token required")

    payload = decode_token(refresh_token_str)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {"access_token": new_access, "token_type": "bearer"}


# ── POST /users ─────────────────────────────────────────────────────────────
@router.post("/users", response_model=UserOut)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        return UserOut(
            status="already registered",
            user_id=existing_user.id,
            is_verified=existing_user.is_verified,
        )

    # Hash the password before storing
    hashed_pw = hash_password(user.password)

    db_user = User(
        email=user.email,
        name=user.name,
        verification_otp=user.verification_otp,
        password=hashed_pw,
        is_verified=user.is_verified,
        credits=10,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return UserOut(
        status="created",
        user_id=db_user.id,
        is_verified=db_user.is_verified,
    )


# ── POST /auth/google ───────────────────────────────────────────────────────
@router.post("/auth/google", response_model=AuthResponse)
async def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    user_info = verify_google_user(req.token)
    if isinstance(user_info, str):
        raise HTTPException(status_code=400, detail=user_info)

    email = user_info.get("email")
    full_name = user_info.get("name") or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()

    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            name=full_name or "Google User",
            is_verified="True",
            auth_method="google",
            credits=10,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        login_status = "registered"
    else:
        login_status = "logged_in"

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return {
        "status": login_status,
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "access_token": access_token,
    }


# ── POST /{user_id}/visual ─────────────────────────────────────────────────
@router.post("/{user_id}/visual", response_model=Visual_Out)
def visual_add(user_id: uuid.UUID, payload: Visual_In, db: Session = Depends(get_db)):
    user_exists = db.query(User).filter(User.id == user_id).first()
    if not user_exists:
        raise HTTPException(status_code=404, detail="User Not Found")

    COST = 2
    if (user_exists.credits or 0) < 99999:
        if (user_exists.credits or 0) < COST:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits ({user_exists.credits}). Please top up on the Plans page.",
            )
        user_exists.credits -= COST
        db.add(user_exists)

    try:
        if payload.item == "PPT":
            if not payload.slides or len(payload.slides) == 0:
                raise HTTPException(status_code=400, detail="Slides data required for PPT generation")
            prompt = ppt_prompt(payload.topic, payload.slides)
        else:
            prompt = visualization_prompt(payload.topic, payload.detail)

        html_code = generate(prompt)
        path = create_and_upload_html(html_content=html_code, title=payload.topic)

        visual = Visual(
            user_id=user_id,
            detail=payload.detail,
            html_code=path,
            topic=payload.topic or "Untitled",
            item=payload.item,
        )
        db.add(visual)
        db.commit()
        db.refresh(visual)

        return {"status": "Success", "visual_id": visual.id, "path": path}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ── POST /visual/split-slides ──────────────────────────────────────────────
@router.post("/visual/split-slides")
def split_slides(payload: SplitSlidesRequest):
    try:
        slides = split_slides_with_ai(payload.topic, payload.content)
        return {"slides": slides}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to split slides: {str(e)}")


# ── POST /visual/{visual_id}/edit ──────────────────────────────────────────
@router.post("/visual/{visual_id}/edit")
def edit_visual(visual_id: uuid.UUID, payload: dict, db: Session = Depends(get_db)):
    user_id = payload.get("user_id")
    instructions = payload.get("instructions", "")

    if not instructions:
        raise HTTPException(status_code=400, detail="Edit instructions required")

    visual = db.query(Visual).filter(Visual.id == visual_id, Visual.user_id == user_id).first()
    if not visual:
        raise HTTPException(status_code=404, detail="Visualization not found")

    try:
        resp = httpx.get(visual.html_code, timeout=15)
        original_html = resp.text
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch original HTML from S3")

    try:
        prompt = edit_prompt(original_html, instructions)
        edited_html = generate(prompt)
        new_path = create_and_upload_html(html_content=edited_html, title=visual.topic)

        visual.html_code = new_path
        db.add(visual)
        db.commit()

        return {"status": "Success", "path": new_path}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


# ── DELETE /visual/{visual_id} ─────────────────────────────────────────────
@router.delete("/visual/{visual_id}")
def delete_visual(visual_id: uuid.UUID, user_id: uuid.UUID, db: Session = Depends(get_db)):
    visual = db.query(Visual).filter(Visual.id == visual_id, Visual.user_id == user_id).first()
    if not visual:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(visual)
    db.commit()
    return {"status": "Deleted"}


# ── GET /visual/{user_id} ──────────────────────────────────────────────────
@router.get("/visual/{user_id}")
async def get_user_library(user_id: uuid.UUID, db: Session = Depends(get_db)):
    visuals = db.query(Visual).filter(Visual.user_id == user_id).order_by(Visual.created_at.desc()).all()
    return visuals


# ── GET /visual/edit/{visualization_id} ────────────────────────────────────
@router.get("/visual/edit/{visualization_id}")
async def get_visual_for_edit(visualization_id: uuid.UUID, db: Session = Depends(get_db)):
    visual = db.query(Visual).filter(Visual.id == visualization_id).first()
    if not visual:
        raise HTTPException(status_code=404, detail="Visualization not found")
    return visual


# ── GET /visual/signed-url/{visualization_id} ──────────────────────────────
@router.get("/visual/signed-url/{visualization_id}")
async def get_signed_url(visualization_id: uuid.UUID, db: Session = Depends(get_db)):
    viz = db.query(Visual).filter(Visual.id == visualization_id).first()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")

    try:
        signed_url, expiry = sign_url(viz)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")

    return {"signed_url": signed_url, "expires_in": expiry}


# ── POST /auth/send-otp ────────────────────────────────────────────────────
@router.post("/auth/send-otp")
async def send_otp(req: OTPRequest):
    message = MessageSchema(
        subject="Your Wiz3D Verification Code",
        recipients=[req.email],
        body=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #05050f; color: #fff; border-radius: 16px;">
            <h2 style="color: #a78bfa; margin-bottom: 8px;">Wiz3D</h2>
            <p style="color: #ccc; margin-bottom: 24px;">Your verification code is:</p>
            <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #fff; background: rgba(139,92,246,0.15); padding: 16px 24px; border-radius: 12px; text-align: center;">
                {req.otp}
            </div>
            <p style="color: #666; font-size: 13px; margin-top: 24px;">This code expires in 10 minutes. Do not share it with anyone.</p>
        </div>
        """,
        subtype="html",
    )

    try:
        await fm.send_message(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"message": "OTP sent successfully"}


# ── POST /payments/create (legacy NOWPayments) ─────────────────────────────
@router.post("/payments/create")
async def create_payment(req: CreatePaymentRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    headers = {"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}

    payload = {
        "price_amount": req.amount_usd,
        "price_currency": "usd",
        "pay_currency": "usdtbsc",
        "order_id": str(uuid.uuid4()),
        "order_description": req.description,
        "ipn_callback_url": "https://wizbackend.vercel.app/payments/webhook/crypto",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{NOWPAYMENTS_BASE}/payment", headers=headers, json=payload)

    if response.status_code != 201:
        raise HTTPException(status_code=502, detail=f"NOWPayments error: {response.text}")

    data = response.json()

    payment = Payment(
        user_id=str(req.user_id),
        type=req.type,
        item_id=req.item_id,
        amount_usd=req.amount_usd,
        status="pending",
        nowpay_id=str(data["payment_id"]),
    )
    db.add(payment)
    db.commit()

    return {
        "payment_id": data["payment_id"],
        "pay_address": data["pay_address"],
        "pay_amount": data["pay_amount"],
        "pay_currency": data["pay_currency"],
        "status": data["payment_status"],
    }


# ── GET /payments/status/{payment_id} ─────────────────────────────────────
@router.get("/payments/status/{payment_id}")
async def get_payment_status(payment_id: uuid.UUID, user_id: uuid.UUID, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(
        Payment.nowpay_id == str(payment_id),
        Payment.user_id == str(user_id),
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status in ("finished", "confirmed"):
        return {"status": payment.status}

    headers = {"x-api-key": NOWPAYMENTS_API_KEY}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{NOWPAYMENTS_BASE}/payment/{payment_id}", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch payment status")

    data = response.json()
    new_status = data.get("payment_status", "pending")

    if new_status in ("finished", "confirmed") and payment.status not in ("finished", "confirmed"):
        payment.status = new_status
        _apply_payment(payment, db)
        db.commit()

    return {"status": new_status}


# ── POST /payments/webhook/crypto (NOWPayments IPN) ────────────────────────
@router.post("/payments/webhook/crypto")
async def payment_webhook_crypto(request: Request, db: Session = Depends(get_db)):
    body = await request.body()

    sig = request.headers.get("x-nowpayments-sig", "")
    expected = hmac.new(
        NOWPAYMENTS_IPN_SECRET.encode(),
        body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(body)
    new_status = data.get("payment_status")
    now_id = str(data.get("payment_id"))

    payment = db.query(Payment).filter(Payment.nowpay_id == now_id).first()
    if not payment:
        return {"ok": True}

    if new_status in ("finished", "confirmed") and payment.status not in ("finished", "confirmed"):
        payment.status = new_status
        _apply_payment(payment, db)
        db.commit()

    return {"ok": True}


def _apply_payment(payment: Payment, db: Session):
    user = db.query(User).filter(User.id == payment.user_id).first()
    if not user:
        return

    if payment.type == "credits":
        credits_to_add = PACK_CREDITS.get(payment.item_id, 0)
        user.credits = (user.credits or 0) + credits_to_add
    elif payment.type == "subscription":
        plan_credits = PLAN_CREDITS.get(payment.item_id, 0)
        user.plan = payment.item_id
        user.credits = plan_credits

    db.add(user)


# ── GET /users/credits/{user_id} ───────────────────────────────────────────
@router.get("/users/credits/{user_id}")
async def get_user_credits(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"user_id": user.id, "credits": user.credits or 0, "plan": user.plan or "free"}


# ── GET /users/profile/{user_id} ───────────────────────────────────────────
@router.get("/users/profile/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user.id,
        "name": user.name or "",
        "email": user.email or "",
        "plan": user.plan or "free",
        "credits": user.credits or 0,
        "role": user.role or "student",
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# ── PATCH /users/profile/name ──────────────────────────────────────────────
@router.patch("/users/profile/name")
def update_name(payload: UpdateNameRequest, db: Session = Depends(get_db)):
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    if len(payload.name.strip()) > 60:
        raise HTTPException(status_code=400, detail="Name too long (max 60 chars)")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.name = payload.name.strip()
    db.add(user)
    db.commit()

    return {"status": "updated", "name": user.name}


# ── PATCH /users/profile/password ─────────────────────────────────────────
@router.patch("/users/profile/password")
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.current_password, user.password or ""):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="New password must be different from current")

    user.password = hash_password(payload.new_password)
    db.add(user)
    db.commit()

    return {"status": "password updated"}


# ── POST /class-plans/generate ─────────────────────────────────────────────
@router.post("/class-plans/generate")
async def generate_plan_endpoint(payload: GeneratePlanRequest, db: Session = Depends(get_db)):
    user_exists = db.query(User).filter(User.id == payload.user_id).first()
    if not user_exists:
        raise HTTPException(status_code=404, detail="User not found")

    COST = 2
    if (user_exists.credits or 0) < 99999:
        if (user_exists.credits or 0) < COST:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits ({user_exists.credits}). Please top up on the Plans page.",
            )
        user_exists.credits -= COST
        db.add(user_exists)

    try:
        prompt = build_plan_prompt(payload)
        response = plan_generate(prompt)
        lectures = response
        if not isinstance(lectures, list) or len(lectures) == 0:
            raise ValueError("Empty plan")
        db.commit()
        return {"plan": lectures}

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned invalid format. Please try again.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ── POST /class-plans/save ─────────────────────────────────────────────────
@router.post("/class-plans/save")
async def save_plan(payload: SavePlanRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.plan_id:
        plan = db.query(ClassPlan).filter(
            ClassPlan.id == payload.plan_id, ClassPlan.user_id == payload.user_id
        ).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
    else:
        plan = ClassPlan(user_id=payload.user_id)
        db.add(plan)

    plan.class_name = payload.class_name
    plan.subject = payload.subject
    plan.outline = payload.outline
    plan.total_lectures = payload.total_lectures
    plan.hours_per_lecture = payload.hours_per_lecture
    plan.age_min = payload.age_min
    plan.age_max = payload.age_max
    plan.education_level = payload.education_level
    plan.books_names = ", ".join([b.strip() for b in (payload.books_names or "").split(",") if b.strip()])
    plan.generated_plan = payload.generated_plan

    db.commit()
    db.refresh(plan)

    return {"plan_id": plan.id, "class_name": plan.class_name, "subject": plan.subject, "status": "saved"}


# ── GET /class-plans/{user_id} ─────────────────────────────────────────────
@router.get("/class-plans/{user_id}")
async def get_user_plans(user_id: uuid.UUID, db: Session = Depends(get_db)):
    plans = db.query(ClassPlan).filter(ClassPlan.user_id == user_id).order_by(ClassPlan.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "class_name": p.class_name,
            "subject": p.subject,
            "total_lectures": p.total_lectures,
            "hours_per_lecture": p.hours_per_lecture,
            "age_min": p.age_min,
            "age_max": p.age_max,
            "education_level": p.education_level,
            "books_names": p.books_names or "",
            "has_plan": p.generated_plan is not None,
            "has_visual": p.visual_url is not None,
            "visual_url": p.visual_url,
            "created_at": p.created_at.isoformat(),
        }
        for p in plans
    ]


# ── GET /class-plans/detail/{plan_id} ─────────────────────────────────────
@router.get("/class-plans/detail/{plan_id}")
async def get_plan_detail(plan_id: uuid.UUID, db: Session = Depends(get_db)):
    plan = db.query(ClassPlan).filter(ClassPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    books = [b.strip() for b in (plan.books_names or "").split(",") if b.strip()]

    return {
        "id": plan.id,
        "class_name": plan.class_name,
        "subject": plan.subject,
        "outline": plan.outline,
        "total_lectures": plan.total_lectures,
        "hours_per_lecture": plan.hours_per_lecture,
        "age_min": plan.age_min,
        "age_max": plan.age_max,
        "education_level": plan.education_level,
        "books_names": books,
        "generated_plan": plan.generated_plan,
        "visual_url": plan.visual_url,
        "created_at": plan.created_at.isoformat(),
    }


# ── DELETE /class-plans/{plan_id} ─────────────────────────────────────────
@router.delete("/class-plans/{plan_id}")
async def delete_plan(plan_id: uuid.UUID, user_id: uuid.UUID, db: Session = Depends(get_db)):
    plan = db.query(ClassPlan).filter(ClassPlan.id == plan_id, ClassPlan.user_id == user_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    db.delete(plan)
    db.commit()
    return {"status": "deleted"}


# ── Helper: verify user is group creator ───────────────────────────────────
def get_group_or_403(group_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.created_by != user_id:
        raise HTTPException(status_code=403, detail="Only the group creator can do this")
    return group


# ── POST /groups/create ────────────────────────────────────────────────────
@router.post("/groups/create")
async def create_group(payload: CreateGroupRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.created_by).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Group name is required")

    group = Group(
        name=payload.name,
        description=payload.description or "",
        privacy=getattr(payload, "privacy", "private") or "private",
        subject=getattr(payload, "subject", None),
        created_by=payload.created_by,
    )
    db.add(group)
    db.flush()

    db.add(GroupMember(group_id=group.id, user_id=payload.created_by, email=user.email))
    db.commit()
    db.refresh(group)

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "privacy": group.privacy or "private",
        "subject": group.subject,
        "created_by": group.created_by,
        "members": 1,
        "created_at": group.created_at.isoformat(),
    }


# ── GET /groups/{user_id} ─────────────────────────────────────────────────
@router.get("/groups/{user_id}")
async def get_user_groups(user_id: uuid.UUID, db: Session = Depends(get_db)):
    memberships = db.query(GroupMember).filter(GroupMember.user_id == user_id).all()
    group_ids = [m.group_id for m in memberships]
    groups = db.query(Group).filter(Group.id.in_(group_ids)).order_by(Group.created_at.desc()).all()

    return [
        {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "privacy": g.privacy or "private",
            "subject": g.subject,
            "created_by": g.created_by,
            "is_creator": g.created_by == user_id,
            "members": len(g.members),
            "created_at": g.created_at.isoformat(),
        }
        for g in groups
    ]


# ── GET /groups/detail/{group_id} ─────────────────────────────────────────
@router.get("/groups/detail/{group_id}")
async def get_group_detail(group_id: uuid.UUID, requesting_user: uuid.UUID, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    is_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id, GroupMember.user_id == requesting_user
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    members = []
    for m in group.members:
        u = db.query(User).filter(User.id == m.user_id).first() if m.user_id else None
        members.append({
            "id": m.id,
            "email": m.email,
            "name": u.name if u else m.email.split("@")[0],
            "joined_at": m.joined_at.isoformat(),
        })

    messages = []
    for msg in sorted(group.messages, key=lambda x: x.created_at):
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        messages.append({
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "sender_name": sender.name if sender else "Unknown",
            "created_at": msg.created_at.isoformat(),
        })

    shares = []
    for s in sorted(group.shares, key=lambda x: x.created_at, reverse=True):
        shares.append({
            "id": s.id,
            "content_type": s.content_type,
            "content_id": s.content_id,
            "title": s.title,
            "url": s.url,
            "created_at": s.created_at.isoformat(),
        })

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "privacy": group.privacy or "private",
        "subject": group.subject,
        "created_by": group.created_by,
        "is_creator": group.created_by == requesting_user,
        "members": members,
        "messages": messages,
        "shares": shares,
    }


# ── POST /groups/add-member ────────────────────────────────────────────────
@router.post("/groups/add-member")
async def add_member(payload: AddMemberRequest, db: Session = Depends(get_db)):
    get_group_or_403(payload.group_id, payload.created_by, db)

    existing = db.query(GroupMember).filter(
        GroupMember.group_id == payload.group_id,
        GroupMember.email == payload.email.lower().strip(),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This email is already a member")

    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()

    member = GroupMember(
        group_id=payload.group_id,
        user_id=user.id if user else None,
        email=payload.email.lower().strip(),
    )
    db.add(member)
    db.commit()

    return {
        "status": "added",
        "email": payload.email,
        "name": user.name if user else None,
        "user_found": user is not None,
    }


# ── DELETE /groups/remove-member/{member_id} ──────────────────────────────
@router.delete("/groups/remove-member/{member_id}")
async def remove_member(member_id: uuid.UUID, created_by: uuid.UUID, db: Session = Depends(get_db)):
    member = db.query(GroupMember).filter(GroupMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    get_group_or_403(member.group_id, created_by, db)

    group = db.query(Group).filter(Group.id == member.group_id).first()
    if member.user_id == group.created_by:
        raise HTTPException(status_code=400, detail="Cannot remove the group creator")

    db.delete(member)
    db.commit()
    return {"status": "removed"}


# ── POST /groups/message ───────────────────────────────────────────────────
@router.post("/groups/message")
async def send_message(payload: SendMessageRequest, db: Session = Depends(get_db)):
    is_member = db.query(GroupMember).filter(
        GroupMember.group_id == payload.group_id, GroupMember.user_id == payload.sender_id
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    msg = GroupMessage(
        group_id=payload.group_id,
        sender_id=payload.sender_id,
        content=payload.content.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    sender = db.query(User).filter(User.id == payload.sender_id).first()

    return {
        "id": msg.id,
        "content": msg.content,
        "sender_id": msg.sender_id,
        "sender_name": sender.name if sender else "Unknown",
        "created_at": msg.created_at.isoformat(),
    }


# ── POST /groups/share ─────────────────────────────────────────────────────
@router.post("/groups/share")
async def share_content(payload: ShareContentRequest, db: Session = Depends(get_db)):
    get_group_or_403(payload.group_id, payload.shared_by, db)

    title = None
    url = None

    if payload.content_type == "visualization":
        visual = db.query(Visual).filter(Visual.id == payload.content_id).first()
        if not visual:
            raise HTTPException(status_code=404, detail="Visualization not found")
        title = visual.topic
        url = visual.html_code
    elif payload.content_type == "class_plan":
        plan = db.query(ClassPlan).filter(ClassPlan.id == payload.content_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Class plan not found")
        title = f"{plan.class_name} — {plan.subject}"
        url = plan.visual_url
    else:
        raise HTTPException(status_code=400, detail="content_type must be 'visualization' or 'class_plan'")

    share = GroupShare(
        group_id=payload.group_id,
        shared_by=payload.shared_by,
        content_type=payload.content_type,
        content_id=payload.content_id,
        title=title,
        url=url,
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    return {
        "id": share.id,
        "title": share.title,
        "content_type": share.content_type,
        "url": share.url,
        "created_at": share.created_at.isoformat(),
    }


# ── DELETE /groups/{group_id} ──────────────────────────────────────────────
@router.delete("/groups/{group_id}")
async def delete_group(group_id: uuid.UUID, created_by: uuid.UUID, db: Session = Depends(get_db)):
    group = get_group_or_403(group_id, created_by, db)
    db.delete(group)
    db.commit()
    return {"status": "deleted"}
