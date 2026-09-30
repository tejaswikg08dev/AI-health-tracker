# ============================================================================
# Health Tracker — Application Configuration
# ============================================================================
# WHAT THIS FILE DOES:
#   Reads ALL configuration from environment variables (or .env file).
#   Uses Pydantic Settings — validates types, provides defaults, errors on missing.
#
# WHY:
#   - Never hardcode secrets (DB password, API keys) in code
#   - Same code runs in dev, staging, production — only env vars change
#   - Pydantic validates everything at startup — fail fast if config is wrong
#
# HOW COMPANIES DO IT:
#   Same pattern. Config from env vars, validated at startup.
#   Some use AWS Secrets Manager or HashiCorp Vault for secrets,
#   but the code pattern is identical — read from env, validate, use.
# ============================================================================

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic Settings automatically:
    1. Reads from environment variables (case-insensitive)
    2. Reads from .env file if it exists
    3. Validates types (str, int, bool, etc.)
    4. Raises clear errors if required vars are missing
    """

    # ── App ──
    APP_NAME: str = "Health Tracker"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Database ──
    # postgresql+asyncpg:// = async driver for FastAPI
    DATABASE_URL: str = "postgresql+asyncpg://healthuser:healthpass@localhost:5432/healthtracker"
    # postgresql:// = sync driver for Alembic migrations
    DATABASE_URL_SYNC: str = "postgresql://healthuser:healthpass@localhost:5432/healthtracker"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Security ──
    SECRET_KEY: str = "change-me-to-a-random-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Algorithm used for JWT signing — HS256 is HMAC with SHA-256
    JWT_ALGORITHM: str = "HS256"

    # ── LLM ──
    LLM_PROVIDER: Literal["ollama", "groq", "openai"] = "ollama"
    LLM_MODEL: str = "llama3.1:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── Embeddings ──
    EMBEDDING_PROVIDER: Literal["ollama", "openai"] = "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # ── Object Storage (S3 / MinIO) ──
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "health-tracker"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGION: str = "us-east-1"

    # ── Email ──
    EMAIL_PROVIDER: Literal["console", "resend", "ses"] = "console"
    RESEND_API_KEY: str = ""
    SES_FROM_EMAIL: str = "noreply@healthtracker.app"

    # ── CORS ──
    # Comma-separated list of allowed origins for frontend
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── AWS ──
    AWS_REGION: str = "us-east-1"
    SQS_EXPORT_QUEUE_URL: str = ""
    SQS_STREAK_QUEUE_URL: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    # Tell Pydantic Settings where to find the .env file
    model_config = SettingsConfigDict(
        env_file=".env",           # Read from .env file in project root
        env_file_encoding="utf-8",
        case_sensitive=False,      # DATABASE_URL and database_url both work
        extra="ignore",            # Ignore unknown env vars (don't crash)
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached).

    WHY @lru_cache:
      Settings are read from env vars and .env file. This is I/O.
      We only need to do it ONCE — then reuse the same Settings object.
      lru_cache ensures get_settings() is called once, result is cached forever.

    This is a common pattern in FastAPI applications.
    """
    return Settings()
