from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from routes.routes import router
from routes.payment_routes import router as payment_router
from routes.generation_routes import router as generation_router
from routes.admin_routes import router as admin_router
from routes.quiz_routes import router as quiz_router
from routes.summarize_routes import router as summarize_router
from routes.research_routes import router as research_router
from routes.feedback_routes import router as feedback_router
from routes.dashboard_routes import router as dashboard_router
from routes.review_routes import router as review_router
from routes.connection_routes import router as connection_router
from routes.message_routes import router as message_router
from routes.studyroom_routes import router as studyroom_router
from routes.research_doc_routes import router as research_doc_router
from routes.analytics_routes import router as analytics_router
# <<<<<<< devin/1779614172-plan-feature-restrictions
from routes.plan_routes import router as plan_router, public_router as plan_public_router
# =======
from routes.group_feed_routes import router as group_feed_router
# >>>>>>> main
from middleware.rate_limiter import limiter, rate_limit_exceeded_handler
import models.models

app = FastAPI(
    title="WizAI API",
    description="Production-ready API for 3D/4D AI generation platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://wizai.vercel.app",
        "https://wiz-ai.vercel.app",
        "https://wizcanv.vercel.app",
        "https://wizcanv.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(payment_router)
app.include_router(generation_router)
app.include_router(admin_router)
app.include_router(quiz_router)
app.include_router(summarize_router)
app.include_router(research_router)
app.include_router(feedback_router)
app.include_router(dashboard_router)
app.include_router(review_router)
app.include_router(connection_router)
app.include_router(message_router)
app.include_router(studyroom_router)
app.include_router(research_doc_router)
app.include_router(analytics_router)
# <<<<<<< devin/1779614172-plan-feature-restrictions
app.include_router(plan_router)
app.include_router(plan_public_router)
# =======
app.include_router(group_feed_router)
# >>>>>>> main


@app.get("/")
def root():
    return {
        "message": "WizAI API is running",
        "status": "healthy",
        "version": "2.0.0",
        "docs": "/docs",
                "endpoints": {
                    "auth": ["/login", "/users", "/auth/google", "/auth/refresh", "/auth/send-otp"],
                    "generation": ["/api/v1/generate/3d", "/api/v1/generate/4d", "/api/v1/generate/model-3d", "/api/v1/generate/batch"],
                    "payments": ["/payments/plans", "/payments/checkout", "/payments/card", "/payments/webhook"],
                    "templates": ["/api/v1/templates"],
                    "analytics": ["/api/v1/analytics/usage"],
                    "admin": ["/admin/dashboard", "/admin/users", "/admin/revenue", "/admin/financials", "/admin/apis", "/admin/services", "/admin/reviews"],
                    "reviews": ["/api/reviews/submit", "/api/reviews/approved", "/api/reviews/my-review"],
                    "quiz": ["/api/v1/quiz/generate", "/api/v1/quiz/submit", "/api/v1/quiz/list"],
                    "summarize": ["/api/v1/summarize/", "/api/v1/summarize/customize-lecture"],
                    "research": ["/api/v1/research/scholar", "/api/v1/research/scholar/cite", "/api/v1/research/documents", "/api/v1/research/ai-assist"],
                    "feedback": ["/api/v1/feedback"],
                    "notes": ["/api/v1/notes"],
                    "dashboard": ["/api/v1/dashboard/stats"],
                    "connections": ["/api/v1/connections", "/api/v1/connections/request", "/api/v1/connections/respond", "/api/v1/connections/suggested"],
                    "messages": ["/api/v1/messages/conversations", "/api/v1/messages/send"],
                    "study_rooms": ["/api/v1/study-rooms"],
                    "analytics_user": ["/api/v1/analytics/my"],
                    "plans": ["/api/v1/plans", "/api/v1/plans/my-features"],
                    "admin_plans": ["/admin/plans"],
                },
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}
