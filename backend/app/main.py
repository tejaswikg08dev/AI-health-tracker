# ============================================================================
# Health Tracker — FastAPI Application Entry Point
# ============================================================================
# WHAT THIS FILE DOES:
#   Creates and configures the FastAPI application.
#   This is the FIRST file that runs when the server starts.
#
# KEY CONCEPTS:
#   App Factory  — create_app() function builds the app (testable, configurable)
#   Lifespan     — startup/shutdown events (connect DB, close connections)
#   Middleware   — code that runs on EVERY request (logging, CORS, rate limiting)
#   Routers      — organize endpoints by module (auth, habits, logs, etc.)
#
# REQUEST FLOW:
#   Client → Nginx → FastAPI (middleware chain) → Router → Handler → Response
#   Each middleware can inspect/modify the request before it reaches the handler.
# ============================================================================

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.redis_client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan — runs code on startup and shutdown.

    WHAT IS LIFESPAN:
      Code before 'yield' runs when the server STARTS.
      Code after 'yield' runs when the server STOPS.

    WHY:
      - Startup: verify DB connection, create MinIO bucket, log config
      - Shutdown: close DB pool, close Redis connections, cleanup resources

    Without proper shutdown, you'd leak database connections.
    In production with 4 workers, that's 4 × 20 pool_size = 80 leaked connections.
    Eventually the database refuses new connections and the app crashes.
    """
    # ── Startup ──
    settings = get_settings()

    # Configure structured logging FIRST — so all other startup logs are formatted
    from app.shared.logging import setup_logging
    setup_logging()

    print(f"🚀 Starting {settings.APP_NAME} v{__version__}")
    print(f"   Environment: {settings.APP_ENV}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   LLM Provider: {settings.LLM_PROVIDER}")
    print(f"   Database: {settings.DATABASE_URL.split('@')[-1]}")  # Log host only, not password

    yield  # Application is running and handling requests

    # ── Shutdown ──
    print("🛑 Shutting down...")
    await close_redis()
    # SQLAlchemy engine cleanup happens automatically via garbage collection,
    # but we could call: await engine.dispose() if needed.
    print("✅ Shutdown complete.")


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI app.

    WHY A FACTORY FUNCTION (not a global variable):
      1. Testable — tests can create a fresh app with different settings
      2. Configurable — pass different settings for dev/staging/prod
      3. Clean — all setup logic in one place

    This pattern is used in Flask (create_app), Django (get_wsgi_application),
    Express.js (createApp), and Spring Boot (@SpringBootApplication).
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Powered Personal Health & Habit Tracker API",
        version=__version__,
        # Lifespan handles startup/shutdown events
        lifespan=lifespan,
        # API docs URL — visit http://localhost:8000/docs to see Swagger UI
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── Register Error Handlers ──
    # Must be registered before middleware so errors from middleware are caught too.
    from app.middleware.error_handler import register_error_handlers
    register_error_handlers(app)

    # ── Register Middleware ──
    # Middleware runs on EVERY request in order.
    # CORS must be first — it handles preflight OPTIONS requests.
    _register_middleware(app, settings)

    # ── Register Routers ──
    # Each module's routes are grouped under a prefix.
    _register_routers(app)

    # ── Health Check ──
    # Simple endpoint for load balancers and monitoring.
    # ALB/Nginx hits this every 30s to verify the app is alive.
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "version": __version__,
            "environment": settings.APP_ENV,
        }

    return app


def _register_middleware(app: FastAPI, settings: get_settings) -> None:
    """
    Register all middleware in the correct order.

    MIDDLEWARE ORDER MATTERS:
      Outermost (first added) runs first on request, last on response.
      Think of it like layers of an onion:

      Request  → CORS → Logging → Rate Limit → Error Handler → Route Handler
      Response ← CORS ← Logging ← Rate Limit ← Error Handler ← Route Handler

    WHY CORS FIRST:
      Browser sends a preflight OPTIONS request before actual API calls.
      CORS middleware must handle this BEFORE any other middleware runs.
      Without CORS, your React frontend can't talk to the API.
    """
    # CORS — Cross-Origin Resource Sharing
    # Allows your React frontend (localhost:3000) to call the API (localhost:8000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,       # Allow cookies and auth headers
        allow_methods=["*"],          # GET, POST, PUT, DELETE, etc.
        allow_headers=["*"],          # Authorization, Content-Type, etc.
    )

    # Logging middleware — logs every request with timing and request_id
    from app.middleware.logging_middleware import LoggingMiddleware
    app.add_middleware(LoggingMiddleware)

    # Rate limiter — prevents abuse, brute force, and expensive AI spam
    from app.middleware.rate_limiter import RateLimiterMiddleware
    app.add_middleware(RateLimiterMiddleware)


def _register_routers(app: FastAPI) -> None:
    """
    Register all module routers with their URL prefixes.

    URL DESIGN:
      /api/v1/auth/...        → Auth module
      /api/v1/habits/...      → Habits module
      /api/v1/logs/...        → Logs module
      /api/v1/analytics/...   → Analytics module
      /api/v1/ai/...          → AI module
      /api/v1/notifications/  → Notifications module
      /api/v1/export/...      → Export module

    WHY /api/v1/:
      - /api/ distinguishes API routes from frontend routes (Nginx routes / to React)
      - /v1/ allows versioning — when you make breaking changes, add /v2/
        without breaking existing clients. This is standard REST practice.
    """
    from app.modules.auth.router import router as auth_router
    from app.modules.habits.router import router as habits_router
    from app.modules.logs.router import router as logs_router
    from app.modules.analytics.router import router as analytics_router
    from app.modules.ai.router import router as ai_router
    from app.modules.notifications.router import router as notifications_router
    from app.modules.export.router import router as export_router

    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
        tags=["Authentication"],
    )

    app.include_router(
        habits_router,
        prefix="/api/v1/habits",
        tags=["Habits"],
    )

    app.include_router(
        logs_router,
        prefix="/api/v1/logs",
        tags=["Logs"],
    )

    app.include_router(
        analytics_router,
        prefix="/api/v1/analytics",
        tags=["Analytics"],
    )

    app.include_router(
        ai_router,
        prefix="/api/v1/ai",
        tags=["AI"],
    )

    app.include_router(
        notifications_router,
        prefix="/api/v1/notifications",
        tags=["Notifications"],
    )

    app.include_router(
        export_router,
        prefix="/api/v1/export",
        tags=["Export"],
    )


# ── Create the app instance ──
# This is what uvicorn/gunicorn imports: "app.main:app"
app = create_app()
