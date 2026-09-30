# ============================================================================
# Health Tracker — Global Error Handler
# ============================================================================
# WHAT THIS FILE DOES:
#   Catches ALL exceptions and converts them to structured JSON responses.
#   Without this, unhandled exceptions return ugly HTML 500 errors.
#
# WHY:
#   Your frontend expects JSON responses — always. Even on errors.
#   This middleware guarantees every error returns:
#     {"error_code": "...", "message": "...", "detail": "..."}
#
# HOW IT WORKS:
#   1. FastAPI exception handlers are registered for specific exception types
#   2. When any code raises an exception, FastAPI finds the matching handler
#   3. The handler converts it to a JSONResponse with the correct status code
#
# REQUEST FLOW ON ERROR:
#   Route handler raises NotFoundError("Habit not found")
#   → FastAPI catches BaseAppError
#   → app_error_handler() converts to {"error_code": "NOT_FOUND", "message": "Habit not found"}
#   → Returns HTTP 404 with JSON body
# ============================================================================

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.exceptions import BaseAppError
from app.shared.logging import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI app.

    Called once during app startup (in main.py).
    """

    @app.exception_handler(BaseAppError)
    async def app_error_handler(request: Request, exc: BaseAppError) -> JSONResponse:
        """
        Handle our custom application errors.

        These are EXPECTED errors — a user did something wrong or
        a resource wasn't found. Log at warning level, not error.

        Examples:
            NotFoundError → 404
            ConflictError → 409
            UnauthorizedError → 401
        """
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors.

        These happen when the request body/query doesn't match the schema.
        Example: POST /habits with {"name": 123} when name should be a string.

        Pydantic gives detailed error info — we pass it through.
        """
        # Extract readable error messages from Pydantic errors
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")

        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=errors,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": errors,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Handle standard HTTP exceptions (404 for unknown routes, 405 method not allowed, etc.).

        These are raised by FastAPI/Starlette itself, not our code.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": exc.detail or "An HTTP error occurred",
                "detail": None,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all for unexpected errors.

        These are BUGS — something we didn't anticipate.
        Log at error level with full traceback for debugging.

        IMPORTANT: In production, NEVER expose the actual error message to the user.
        It might contain sensitive info (SQL queries, file paths, API keys).
        Return a generic message and log the real error server-side.
        """
        logger.error(
            "unhandled_error",
            error_type=type(exc).__name__,
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            exc_info=exc,  # structlog will format the full traceback
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "detail": None,
            },
        )
