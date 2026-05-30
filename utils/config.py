import os
from dotenv import load_dotenv
from fastapi_mail import FastMail, ConnectionConfig

load_dotenv()

# ── App Config ──────────────────────────────────────────────────────────────
APP_NAME = "WizAI"
APP_VERSION = "2.0.0"
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://wizai.vercel.app")

# ── JWT Config ──────────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "wiz3d-jwt-secret-change-in-production-2024")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# ── Stripe Config ───────────────────────────────────────────────────────────
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ── NOWPayments (legacy crypto) ─────────────────────────────────────────────
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY", "")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
NOWPAYMENTS_BASE = "https://api.nowpayments.io/v1"

# ── AWS S3 ──────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "")
AWS_REGION = os.getenv("AWS_REGION", "")

# ── AI API Keys ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")

# ── SerpAPI (Google Scholar) ───────────────────────────────────────────────
SERP_API_KEY = os.getenv("SERP_API_KEY", "")

# ── Mail Config ─────────────────────────────────────────────────────────────
mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", ""),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

fm = FastMail(mail_config)

# ── Rate Limiting ───────────────────────────────────────────────────────────
RATE_LIMIT_FREE = "10/hour"
RATE_LIMIT_STARTER = "60/hour"
RATE_LIMIT_PRO = "200/hour"
RATE_LIMIT_BUSINESS = "1000/hour"

# ── Subscription Plans ──────────────────────────────────────────────────────
PLAN_CONFIG = {
    "free": {
        "name": "Free",
        "credits_per_month": 10,
        "price_monthly": 0,
        "price_yearly": 0,
        "features": ["Basic 3D generation", "1 export/day", "Community support"],
        "rate_limit": RATE_LIMIT_FREE,
        "max_exports_per_day": 1,
        "batch_generation": False,
        "api_access": False,
        "priority_queue": False,
        "hd_quality": False,
    },
    "starter": {
        "name": "Starter",
        "credits_per_month": 100,
        "price_monthly": 19,
        "price_yearly": 190,
        "stripe_price_monthly": os.getenv("STRIPE_PRICE_STARTER_MONTHLY", ""),
        "stripe_price_yearly": os.getenv("STRIPE_PRICE_STARTER_YEARLY", ""),
        "features": ["HD quality output", "Unlimited exports", "All formats (GLB, GLTF, OBJ)", "Email support", "Template gallery"],
        "rate_limit": RATE_LIMIT_STARTER,
        "max_exports_per_day": -1,
        "batch_generation": False,
        "api_access": False,
        "priority_queue": False,
        "hd_quality": True,
    },
    "pro": {
        "name": "Pro",
        "credits_per_month": 500,
        "price_monthly": 49,
        "price_yearly": 490,
        "stripe_price_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""),
        "stripe_price_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY", ""),
        "features": ["Everything in Starter", "Priority generation queue", "Batch generation", "API access", "4D animations", "Priority support"],
        "rate_limit": RATE_LIMIT_PRO,
        "max_exports_per_day": -1,
        "batch_generation": True,
        "api_access": True,
        "priority_queue": True,
        "hd_quality": True,
    },
    "business": {
        "name": "Business",
        "credits_per_month": 2000,
        "price_monthly": 149,
        "price_yearly": 1490,
        "stripe_price_monthly": os.getenv("STRIPE_PRICE_BUSINESS_MONTHLY", ""),
        "stripe_price_yearly": os.getenv("STRIPE_PRICE_BUSINESS_YEARLY", ""),
        "features": ["Everything in Pro", "Team seats (up to 10)", "White-label embeds", "Custom branding", "SLA guarantee", "Dedicated support"],
        "rate_limit": RATE_LIMIT_BUSINESS,
        "max_exports_per_day": -1,
        "batch_generation": True,
        "api_access": True,
        "priority_queue": True,
        "hd_quality": True,
    },
    "enterprise": {
        "name": "Enterprise",
        "credits_per_month": 99999,
        "price_monthly": 0,
        "price_yearly": 0,
        "features": ["Unlimited everything", "Custom AI models", "Dedicated infrastructure", "Custom integrations", "24/7 support", "On-premise option"],
        "rate_limit": RATE_LIMIT_BUSINESS,
        "max_exports_per_day": -1,
        "batch_generation": True,
        "api_access": True,
        "priority_queue": True,
        "hd_quality": True,
    },
}

# Credit pack pricing
CREDIT_PACKS = {
    "credits_50": {"credits": 50, "price_usd": 5.00},
    "credits_100": {"credits": 100, "price_usd": 9.00},
    "credits_250": {"credits": 250, "price_usd": 20.00},
    "credits_500": {"credits": 500, "price_usd": 35.00},
    "credits_1000": {"credits": 1000, "price_usd": 60.00},
}
