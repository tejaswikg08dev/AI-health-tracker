# ============================================================================
# Health Tracker — Request/Response Logging Middleware
# ============================================================================
# WHAT THIS FILE DOES:
#   Logs every HTTP request and response with timing, status, and context.
#   Every request gets a unique request_id for tracing.
#
# WHY:
#   When a user reports "the app is slow" or "I got an error",
#   you need to find THAT specific request in your logs.
#   Request IDs let you trace a single request across all log entries.
#
# WHAT GETS LOGGED:
#   Request:  method, path, client IP, user-agent, request_id
#   Response: status code, response time (ms)
#
# EXAMPLE LOG OUTPUT:
#   {"event": "http_request", "method": "POST", "path": "/api/v1/auth/login",
#    "status": 200, "duration_ms": 45.2, "request_id": "abc-123"}
# ============================================================================

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.shared.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every HTTP request with timing info.

    HOW MIDDLEWARE WORKS:
      For every request, FastAPI calls dispatch().
      We run code BEFORE the handler (start timer),
      call the handler (call_next),
      then run code AFTER the handler (stop timer, log).

    MIDDLEWARE LIFECYCLE:
      1. Request arrives
      2. dispatch() starts timer, generates request_id
      3. call_next(request) — passes request to the next middleware or route handler
      4. Response comes back
      5. dispatch() logs the request with duration
      6. Returns response to client
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate unique ID for this request — used to trace in logs
        request_id = str(uuid.uuid4())[:8]  # Short 8-char ID (enough for tracing)

        # Attach request_id to request state — accessible in route handlers
        request.state.request_id = request_id

        # Start timing
        start_time = time.perf_counter()

        # Skip logging for health checks (too noisy)
        if request.url.path == "/health":
            return await call_next(request)

        try:
            # Pass request to the route handler
            response = await call_next(request)
        except Exception:
            # If an unhandled exception occurs, log it and re-raise
            # The error_handler will catch it and return proper JSON
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "http_request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=500,
                duration_ms=round(duration_ms, 2),
            )
            raise

        # Calculate how long the request took
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add request_id to response headers — frontend can include it in bug reports
        response.headers["X-Request-ID"] = request_id

        # Log the request
        # Choose log level based on status code:
        #   2xx/3xx → info (everything is fine)
        #   4xx     → warning (client error — bad input, unauthorized)
        #   5xx     → error (server error — our bug)
        log_level = "info"
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"

        getattr(logger, log_level)(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=request.client.host if request.client else "unknown",
        )

        return response
