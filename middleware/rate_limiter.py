from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from utils.config import PLAN_CONFIG


def get_user_identifier(request: Request) -> str:
    # Try to get user_id from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_identifier)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": "You have exceeded your plan's rate limit. Please upgrade your plan or wait before making more requests.",
            "retry_after": exc.detail,
        },
    )


def get_rate_limit_for_plan(plan: str) -> str:
    plan_config = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])
    return plan_config.get("rate_limit", "10/hour")
