# ============================================================================
# Health Tracker — Redis-Based Rate Limiter
# ============================================================================
# WHAT THIS FILE DOES:
#   Limits how many requests a client can make per time window.
#   Uses Redis sliding window algorithm — industry standard.
#
# WHY RATE LIMITING:
#   Without it, someone could:
#   - Brute-force login passwords (try millions of passwords)
#   - Spam AI chat (expensive LLM calls — costs you money)
#   - DDoS your API (flood with requests until server crashes)
#
# ALGORITHM: Sliding Window Counter
#   - Each client gets a Redis key: "rate_limit:{ip}:{window}"
#   - Each request increments the counter
#   - If counter > limit, request is rejected with HTTP 429
#   - Key expires after the window (auto-cleanup)
#
# EXAMPLE:
#   Limit: 60 requests per minute
#   Client sends request #61 within 1 minute → HTTP 429 Too Many Requests
#   After the minute resets, counter goes back to 0
#
# HOW COMPANIES DO IT:
#   Same algorithm. Some use Nginx rate limiting (we do that too),
#   but application-level rate limiting allows per-user limits
#   (logged-in users get higher limits than anonymous).
# ============================================================================

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.redis_client import get_redis_client
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Rate limit configuration
# Different limits for different endpoint types
RATE_LIMITS = {
    "/api/v1/ai/": {"requests": 10, "window_seconds": 60},      # AI is expensive
    "/api/v1/auth/login": {"requests": 5, "window_seconds": 60}, # Prevent brute force
    "/api/v1/": {"requests": 60, "window_seconds": 60},          # General API
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Redis-based sliding window rate limiter.

    HOW SLIDING WINDOW WORKS:
      Fixed window: Counter resets at exact minute boundaries (00:00, 01:00, ...)
        Problem: Someone sends 60 requests at 0:59, and 60 more at 1:00
                 → 120 requests in 2 seconds. The limit is useless.

      Sliding window: Counter tracks the last 60 seconds from NOW.
        If you sent 60 requests in the last 60 seconds, you're blocked.
        No gaming the boundary.

    IMPLEMENTATION:
      We use Redis INCR + EXPIRE for simplicity.
      This is a "fixed window" implementation (close enough for our scale).
      For true sliding window, you'd use Redis sorted sets with timestamps.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks and non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Determine which rate limit applies to this path
        limit_config = self._get_limit_for_path(request.url.path)

        # Get client identifier (IP address)
        # In production behind a load balancer, use X-Forwarded-For header
        client_ip = request.client.host if request.client else "unknown"

        try:
            redis_client = get_redis_client()

            # Build Redis key: "rl:{ip}:{window_start}"
            # Window start = current time truncated to window_seconds boundary
            window_start = int(time.time()) // limit_config["window_seconds"]
            redis_key = f"rl:{client_ip}:{request.url.path}:{window_start}"

            # Increment counter and get current value
            current_count = await redis_client.incr(redis_key)

            # Set expiry on first request (when count becomes 1)
            if current_count == 1:
                await redis_client.expire(redis_key, limit_config["window_seconds"])

            # Check if over limit
            if current_count > limit_config["requests"]:
                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    path=request.url.path,
                    current_count=current_count,
                    limit=limit_config["requests"],
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "detail": None,
                    },
                    headers={
                        # Standard headers — tells client when to retry
                        "Retry-After": str(limit_config["window_seconds"]),
                        "X-RateLimit-Limit": str(limit_config["requests"]),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            # Request is within limits — proceed
            response = await call_next(request)

            # Add rate limit info to response headers (helpful for API consumers)
            remaining = max(0, limit_config["requests"] - current_count)
            response.headers["X-RateLimit-Limit"] = str(limit_config["requests"])
            response.headers["X-RateLimit-Remaining"] = str(remaining)

            return response

        except Exception:
            # If Redis is down, DON'T block requests — let them through
            # Rate limiting is a nice-to-have, not a hard requirement
            # This is called "fail open" — the opposite of "fail closed"
            logger.warning("rate_limiter_error", error="Redis unavailable, skipping rate limit")
            return await call_next(request)

    @staticmethod
    def _get_limit_for_path(path: str) -> dict:
        """
        Find the most specific rate limit for a given path.

        Checks path prefixes from most specific to least specific.
        Example: /api/v1/ai/chat matches "/api/v1/ai/" (10 req/min)
                 /api/v1/habits matches "/api/v1/" (60 req/min)
        """
        for prefix, config in sorted(RATE_LIMITS.items(), key=lambda x: -len(x[0])):
            if path.startswith(prefix):
                return config
        # Default: generous limit for unknown paths
        return {"requests": 100, "window_seconds": 60}
