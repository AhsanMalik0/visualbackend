from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from services.auth_service import get_db, require_auth
from models.models import User, Visual, Template, APIUsageLog
from agent.agents import generate, visualization_prompt, ppt_prompt, split_slides_with_ai
from utils.utils import create_and_upload_html
from utils.config import PLAN_CONFIG

router = APIRouter(prefix="/api/v1", tags=["Generation"])


# ── Request Schemas ─────────────────────────────────────────────────────────
class Generate3DRequest(BaseModel):
    topic: str
    detail: str
    quality: Optional[str] = "standard"  # standard, hd
    style: Optional[str] = None  # cyberpunk, organic, cosmic, etc.


class Generate4DRequest(BaseModel):
    topic: str
    detail: str
    duration_seconds: Optional[int] = 10
    animation_style: Optional[str] = "orbiting"  # orbiting, pulsing, flowing, exploding
    quality: Optional[str] = "standard"


class GenerateFromImageRequest(BaseModel):
    image_url: str
    style: Optional[str] = None
    detail: Optional[str] = ""


class BatchGenerateRequest(BaseModel):
    items: List[Generate3DRequest]


class ExportRequest(BaseModel):
    format: str  # glb, gltf, obj, mp4


class TemplateGenerateRequest(BaseModel):
    template_id: UUID
    parameters: Optional[dict] = None
    topic: Optional[str] = None


# ── Helper: check credits and deduct ───────────────────────────────────────
def check_and_deduct_credits(user: User, cost: int, db: Session):
    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])
    # Enterprise/unlimited users (credits >= 99999)
    if (user.credits or 0) >= 99999:
        return

    if (user.credits or 0) < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits ({user.credits} available, {cost} required). Please upgrade your plan or purchase more credits.",
        )

    user.credits -= cost
    user.total_generations = (user.total_generations or 0) + 1
    user.last_generation_at = datetime.now(timezone.utc)
    db.add(user)


def log_api_usage(user_id: UUID, endpoint: str, method: str, credits_used: int, gen_type: str, status: int, db: Session):
    log = APIUsageLog(
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        credits_used=credits_used,
        generation_type=gen_type,
        response_status=status,
    )
    db.add(log)


# ── POST /api/v1/generate/3d ───────────────────────────────────────────────
@router.post("/generate/3d")
async def generate_3d(
    req: Generate3DRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    cost = 2 if req.quality == "standard" else 4
    check_and_deduct_credits(user, cost, db)

    try:
        prompt = visualization_prompt(req.topic, req.detail)
        html_code = generate(prompt)
        path = create_and_upload_html(html_content=html_code, title=req.topic)

        visual = Visual(
            user_id=user.id,
            detail=req.detail,
            html_code=path,
            topic=req.topic or "Untitled",
            item="Lecture",
            generation_type="3d_visual",
            quality=req.quality,
        )
        db.add(visual)
        db.commit()
        db.refresh(visual)

        log_api_usage(user.id, "/api/v1/generate/3d", "POST", cost, "3d_visual", 200, db)
        db.commit()

        return {
            "status": "success",
            "visual_id": str(visual.id),
            "url": path,
            "credits_remaining": user.credits,
            "generation_type": "3d_visual",
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        log_api_usage(user.id, "/api/v1/generate/3d", "POST", 0, "3d_visual", 500, db)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ── POST /api/v1/generate/4d ───────────────────────────────────────────────
@router.post("/generate/4d")
async def generate_4d(
    req: Generate4DRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    # Check plan allows 4D
    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])
    if user.plan in ("free", "starter"):
        raise HTTPException(
            status_code=403,
            detail="4D animation generation requires Pro plan or higher. Please upgrade.",
        )

    cost = 5 if req.quality == "standard" else 8
    check_and_deduct_credits(user, cost, db)

    try:
        # Enhanced prompt for 4D animation
        animation_prompt = f"""
You are an expert 3D/4D web developer. Create a SELF-CONTAINED HTML file with an animated 3D visualization that includes:

TOPIC: {req.topic}
DETAILS: {req.detail}

ANIMATION REQUIREMENTS:
- Duration: {req.duration_seconds} seconds loop
- Animation style: {req.animation_style}
- Include a TIMELINE CONTROL BAR at the bottom (play/pause, scrubber, time display)
- Include a ZOom In Zoom out features 
- The animation should tell a story or demonstrate a process over time
- Include keyframe markers on the timeline for important moments

TECHNICAL SPECIFICATIONS:
1. Use Three.js r128 (CDN), GSAP 3 (CDN), OrbitControls
2. Timeline UI: A custom playback bar with play/pause button, progress scrubber, and time readout
3. The 3D scene should evolve over time (e.g., objects appear, transform, interact)
4. Include at least 3 distinct "phases" in the animation
5. Background: #050510, accent colors: violet (#8b5cf6) and emerald (#10b981)
6. Responsive, fullscreen canvas
7. Add an overlay panel showing current phase description

OUTPUT: ONLY raw HTML starting with <!DOCTYPE html> and ending with </html>. No markdown, no code fences.
"""
        html_code = generate(animation_prompt)
        path = create_and_upload_html(html_content=html_code, title=f"4D-{req.topic}")

        visual = Visual(
            user_id=user.id,
            detail=req.detail,
            html_code=path,
            topic=req.topic or "Untitled 4D",
            item="4D",
            generation_type="4d_animation",
            quality=req.quality,
        )
        db.add(visual)
        db.commit()
        db.refresh(visual)

        log_api_usage(user.id, "/api/v1/generate/4d", "POST", cost, "4d_animation", 200, db)
        db.commit()

        return {
            "status": "success",
            "visual_id": str(visual.id),
            "url": path,
            "credits_remaining": user.credits,
            "generation_type": "4d_animation",
            "duration_seconds": req.duration_seconds,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"4D generation failed: {str(e)}")


# ── POST /api/v1/generate/model-3d ─────────────────────────────────────────
@router.post("/generate/model-3d")
async def generate_3d_model(
    req: Generate3DRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    cost = 3 if req.quality == "standard" else 6
    check_and_deduct_credits(user, cost, db)

    try:
        model_prompt = f"""
You are an expert Three.js developer and Visual expert. Create a SELF-CONTAINED HTML file that:

1. Describe the Visual for: "{req.topic}" - {req.detail}
1. Renders a detailed 3D/4D MODEL 
2. Includes an EXPORT BUTTON that downloads the scene as a .glb file
3. Uses Three.js r128 + GLTFExporter from CDN

TECHNICAL REQUIREMENTS:
- Import GLTFExporter: https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/exporters/GLTFExporter.js
- The 3D model should be detailed and geometrically accurate
- Add OrbitControls for inspection
- Include a "Download GLB" button (fixed top-right) that exports the scene
- Include a "Download GLTF" button next to it
- Background: #0a0a14
- Good lighting setup (ambient + directional + point lights)
- The model should be suitable for use in other 3D applications

EXPORT CODE (include this):
```
function exportGLB() {{
    const exporter = new THREE.GLTFExporter();
    exporter.parse(scene, (result) => {{
        const blob = new Blob([result], {{type: 'application/octet-stream'}});
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = '{req.topic.replace(" ", "_")}.glb';
        link.click();
    }}, {{binary: true}});
}}
```

OUTPUT: ONLY raw HTML starting with <!DOCTYPE html> and ending with </html>. No markdown, no code fences.
"""
        html_code = generate(model_prompt)
        path = create_and_upload_html(html_content=html_code, title=f"model-{req.topic}")

        visual = Visual(
            user_id=user.id,
            detail=req.detail,
            html_code=path,
            topic=req.topic or "Untitled Model",
            item="Model",
            generation_type="model_3d",
            quality=req.quality,
        )
        db.add(visual)
        db.commit()
        db.refresh(visual)

        log_api_usage(user.id, "/api/v1/generate/model-3d", "POST", cost, "model_3d", 200, db)
        db.commit()

        return {
            "status": "success",
            "visual_id": str(visual.id),
            "url": path,
            "credits_remaining": user.credits,
            "generation_type": "model_3d",
            "export_formats": ["glb", "gltf"],
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"3D model generation failed: {str(e)}")


# ── POST /api/v1/generate/batch ─────────────────────────────────────────────
@router.post("/generate/batch")
async def batch_generate(
    req: BatchGenerateRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Batch generate multiple 3D visualizations (Pro+ only)."""
    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])
    if not plan_config.get("batch_generation"):
        raise HTTPException(
            status_code=403,
            detail="Batch generation requires Pro plan or higher.",
        )

    if len(req.items) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 items per batch")

    total_cost = len(req.items) * 2
    check_and_deduct_credits(user, total_cost, db)

    results = []
    for item in req.items:
        try:
            prompt = visualization_prompt(item.topic, item.detail)
            html_code = generate(prompt)
            path = create_and_upload_html(html_content=html_code, title=item.topic)

            visual = Visual(
                user_id=user.id,
                detail=item.detail,
                html_code=path,
                topic=item.topic or "Untitled",
                item="Lecture",
                generation_type="3d_visual",
                quality=item.quality or "standard",
            )
            db.add(visual)
            db.flush()

            results.append({
                "status": "success",
                "visual_id": str(visual.id),
                "url": path,
                "topic": item.topic,
            })
        except Exception as e:
            results.append({
                "status": "failed",
                "topic": item.topic,
                "error": str(e),
            })

    db.commit()

    return {
        "status": "completed",
        "total": len(req.items),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
        "credits_remaining": user.credits,
    }


# ── GET /api/v1/templates ───────────────────────────────────────────────────
@router.get("/templates")
async def get_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Template)
    if category:
        query = query.filter(Template.category == category)

    templates = query.order_by(Template.usage_count.desc()).all()

    # If no templates in DB, return built-in defaults
    if not templates:
        return {
            "templates": [
                {
                    "id": "builtin-solar-system",
                    "name": "Solar System",
                    "description": "Interactive 3D solar system with orbiting planets",
                    "category": "science",
                    "thumbnail_url": None,
                    "is_premium": False,
                    "parameters": {"planet_count": 8, "show_orbits": True, "animation_speed": 1.0},
                },
                {
                    "id": "builtin-dna-helix",
                    "name": "DNA Double Helix",
                    "description": "Animated DNA replication with base pairs",
                    "category": "science",
                    "thumbnail_url": None,
                    "is_premium": False,
                    "parameters": {"helix_turns": 5, "show_labels": True},
                },
                {
                    "id": "builtin-neural-network",
                    "name": "Neural Network",
                    "description": "3D visualization of a deep learning neural network",
                    "category": "science",
                    "thumbnail_url": None,
                    "is_premium": False,
                    "parameters": {"layers": 4, "neurons_per_layer": 8},
                },
                {
                    "id": "builtin-product-showcase",
                    "name": "Product Showcase",
                    "description": "Rotating 3D product display with lighting",
                    "category": "marketing",
                    "thumbnail_url": None,
                    "is_premium": True,
                    "parameters": {"rotation_speed": 0.5, "background": "gradient"},
                },
                {
                    "id": "builtin-city-flythrough",
                    "name": "City Flythrough",
                    "description": "Procedural city with flythrough camera animation",
                    "category": "architecture",
                    "thumbnail_url": None,
                    "is_premium": True,
                    "parameters": {"building_count": 50, "time_of_day": "night"},
                },
                {
                    "id": "builtin-particle-galaxy",
                    "name": "Particle Galaxy",
                    "description": "Million-particle galaxy simulation",
                    "category": "science",
                    "thumbnail_url": None,
                    "is_premium": False,
                    "parameters": {"particle_count": 50000, "spiral_arms": 4},
                },
                {
                    "id": "builtin-data-dashboard",
                    "name": "3D Data Dashboard",
                    "description": "Interactive 3D charts and data visualization",
                    "category": "marketing",
                    "thumbnail_url": None,
                    "is_premium": True,
                    "parameters": {"chart_type": "bar3d", "data_points": 20},
                },
                {
                    "id": "builtin-game-terrain",
                    "name": "Procedural Terrain",
                    "description": "Infinite procedural terrain with biomes",
                    "category": "gaming",
                    "thumbnail_url": None,
                    "is_premium": True,
                    "parameters": {"biome": "forest", "elevation_scale": 1.0},
                },
            ],
            "categories": ["science", "marketing", "architecture", "gaming", "education"],
        }

    return {
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "thumbnail_url": t.thumbnail_url,
                "is_premium": t.is_premium,
                "parameters": t.parameters,
                "usage_count": t.usage_count,
            }
            for t in templates
        ],
        "categories": list(set(t.category for t in templates)),
    }


# ── POST /api/v1/generate/from-template ────────────────────────────────────
@router.post("/generate/from-template")
async def generate_from_template(
    req: TemplateGenerateRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    cost = 1
    check_and_deduct_credits(user, cost, db)

    # Build a prompt from template parameters
    topic = req.topic or "Template Visualization"
    params_str = ", ".join(f"{k}: {v}" for k, v in (req.parameters or {}).items())

    prompt = visualization_prompt(topic, f"Based on template parameters: {params_str}. {topic}")
    try:
        html_code = generate(prompt)
        path = create_and_upload_html(html_content=html_code, title=topic)

        visual = Visual(
            user_id=user.id,
            detail=f"Template: {req.template_id}, Params: {params_str}",
            html_code=path,
            topic=topic,
            item="Template",
            generation_type="3d_visual",
        )
        db.add(visual)
        db.commit()
        db.refresh(visual)

        return {
            "status": "success",
            "visual_id": str(visual.id),
            "url": path,
            "credits_remaining": user.credits,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Template generation failed: {str(e)}")


# ── GET /api/v1/analytics/usage ─────────────────────────────────────────────
@router.get("/analytics/usage")
async def get_usage_analytics(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func as sql_func

    total_generations = db.query(sql_func.count(Visual.id)).filter(Visual.user_id == user.id).scalar()
    total_credits_used = db.query(sql_func.sum(APIUsageLog.credits_used)).filter(APIUsageLog.user_id == user.id).scalar()

    # Generation breakdown by type
    type_breakdown = (
        db.query(Visual.generation_type, sql_func.count(Visual.id))
        .filter(Visual.user_id == user.id)
        .group_by(Visual.generation_type)
        .all()
    )

    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])

    return {
        "user_id": str(user.id),
        "plan": user.plan,
        "credits_remaining": user.credits or 0,
        "credits_per_month": plan_config["credits_per_month"],
        "total_generations": total_generations or 0,
        "total_credits_used": total_credits_used or 0,
        "generation_breakdown": {t: c for t, c in type_breakdown} if type_breakdown else {},
        "member_since": user.created_at.isoformat() if user.created_at else None,
    }


# ── POST /api/v1/api-keys ──────────────────────────────────────────────────
@router.post("/api-keys")
async def create_api_key(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])
    if not plan_config.get("api_access"):
        raise HTTPException(
            status_code=403,
            detail="API access requires Pro plan or higher.",
        )

    from services.auth_service import generate_api_key

    api_key = generate_api_key()
    user.api_key = api_key
    user.api_key_created_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    return {
        "api_key": api_key,
        "created_at": user.api_key_created_at.isoformat(),
        "note": "Store this key securely. It will not be shown again.",
    }


# ── GET /api/v1/api-keys ───────────────────────────────────────────────────
@router.get("/api-keys")
async def get_api_key_info(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if not user.api_key:
        return {"has_key": False}

    masked = user.api_key[:8] + "..." + user.api_key[-4:]
    return {
        "has_key": True,
        "key_preview": masked,
        "created_at": user.api_key_created_at.isoformat() if user.api_key_created_at else None,
    }
