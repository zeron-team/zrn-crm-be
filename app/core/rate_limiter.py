"""
Rate Limiting Middleware for ZeRoN 360°
Uses Redis sliding window to limit requests per endpoint group.
"""

import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.redis_cache import check_rate_limit

logger = logging.getLogger(__name__)

# Rate limit configs: {path_prefix: (max_requests, window_seconds)}
RATE_LIMITS = {
    "/api/v1/ai/chat": (10, 60),         # 10 requests/min for AI
    "/api/v1/auth/login": (5, 60),        # 5 login attempts/min
    "/api/v1/arca/emit": (30, 60),        # 30 ARCA submissions/min
    "/api/v1/arca/": (60, 60),            # 60 ARCA queries/min
}

DEFAULT_RATE_LIMIT = (120, 60)  # 120 requests/min for everything else


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for non-API routes and health checks
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        # Determine rate limit for this path
        max_req, window = DEFAULT_RATE_LIMIT
        for prefix, limits in RATE_LIMITS.items():
            if path.startswith(prefix) or path == prefix:
                max_req, window = limits
                break

        # Build identifier: prefer user_id from auth, fallback to IP
        client_ip = request.client.host if request.client else "unknown"
        identifier = f"{client_ip}:{path.split('?')[0]}"

        result = check_rate_limit(identifier, max_req, window)

        if not result["allowed"]:
            logger.warning(f"Rate limit exceeded: {identifier} ({max_req}/{window}s)")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": result["retry_after"],
                },
                headers={
                    "Retry-After": str(result["retry_after"]),
                    "X-RateLimit-Limit": str(max_req),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
        return response
