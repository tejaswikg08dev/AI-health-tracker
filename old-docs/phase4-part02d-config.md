# Phase 4 — Part 02d: Application Config (config.py)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 02d |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.1 — FastAPI Foundation |
| **File** | `backend/app/config.py` |
| **Depends On** | Part 02a (requirements.txt — pydantic-settings installed) |
| **Next** | [Part 02e — database.py](./phase4-part02e-database.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~12 minutes |
| **Lines** | ~85 lines |

---

## What is Pydantic Settings? Read This First

Your app needs configuration values: database URL, Redis URL, secret key, LLM provider. These come from environment variables (`.env` file). But raw `os.environ.get()` has problems:

```python
# ❌ Bad: scattered, no validation, no defaults, no type safety
import os
db_url = os.environ.get("DATABASE_URL")  # Returns str or None — no validation
debug = os.environ.get("DEBUG")          # Returns "true" (string!), not True (boolean)
port = os.environ.get("PORT")            # Returns "8000" (string!), not 8000 (int)
```

Pydantic Settings fixes ALL of these:

```python
# ✅ Good: centralized, validated, typed, with defaults
class Settings(BaseSettings):
    DATABASE_URL: str                    # Required — app crashes at startup if missing
    DEBUG: bool = True                   # Automatically converts "true" → True
    PORT: int = 8000                     # Automatically converts "8000" → 8000
    LLM_PROVIDER: Literal["ollama", "groq", "openai"] = "ollama"  # Only 3 valid values
```

**Real-world analogy:** Raw `os.environ` is like shouting orders in a kitchen — anyone can hear anything, nothing is validated. Pydantic Settings is like a printed order ticket — typed, validated, everyone reads the same thing.

---

## Architecture: Where This File Fits

```
.env file
  │
  │ read by Pydantic Settings at startup
  ▼
config.py → Settings class (singleton via @lru_cache)
  │
  │ imported by EVERYTHING:
  ├── database.py     (DATABASE_URL)
  ├── redis_client.py (REDIS_URL)
  ├── security.py     (SECRET_KEY, JWT_ALGORITHM)
  ├── llm/factory.py  (LLM_PROVIDER, LLM_MODEL)
  ├── storage.py      (S3_ENDPOINT, S3_BUCKET)
  ├── email_provider.py (EMAIL_PROVIDER)
  └── main.py          (APP_NAME, DEBUG, APP_ENV)
```

---

## Source Code — Line by Line

> 📁 **File:** `backend/app/config.py`
> 📏 **Lines:** ~85
> ⏱️ **Type time:** ~12 minutes

```python
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
    DATABASE_URL: str = "postgresql+asyncpg://healthuser:healthpass@localhost:5432/healthtracker"
    DATABASE_URL_SYNC: str = "postgresql://healthuser:healthpass@localhost:5432/healthtracker"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Security ──
    SECRET_KEY: str = "change-me-to-a-random-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached).

    @lru_cache ensures get_settings() is called once, result is cached forever.
    Every subsequent call returns the same Settings object — no I/O.
    """
    return Settings()
```

**Line-by-line explanation of key concepts:**

### `Literal["ollama", "groq", "openai"]`
```python
LLM_PROVIDER: Literal["ollama", "groq", "openai"] = "ollama"
```
`Literal` restricts the value to exactly these 3 strings. If `.env` has `LLM_PROVIDER=claude`, Pydantic raises a ValidationError at startup — not a silent bug later.

### `model_config = SettingsConfigDict(...)`
```python
model_config = SettingsConfigDict(
    env_file=".env",           # Read from .env file
    env_file_encoding="utf-8", # Handle Unicode characters
    case_sensitive=False,       # DATABASE_URL and database_url both work
    extra="ignore",             # Unknown env vars don't crash the app
)
```
This tells Pydantic: "Read the `.env` file. If a variable in `.env` doesn't match any field in Settings, just ignore it (don't crash)."

### `@lru_cache()`
```python
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```
`@lru_cache` is a Python decorator that **caches the function's return value**. First call: creates Settings (reads .env file, I/O operation). Every subsequent call: returns the cached object (no I/O, instant).

This is important because `get_settings()` is called from MANY files. Without caching, each call would re-read the .env file. With caching: read once, use forever.

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | Pydantic Settings | Typed, validated configuration from environment variables |
| 2 | Literal types | Restrict a field to specific allowed values |
| 3 | @lru_cache | Cache function results — read .env once, reuse forever |
| 4 | @property | Computed attribute (looks like a field, runs code) |
| 5 | SettingsConfigDict | Configures HOW Pydantic reads env vars (file path, case, extras) |
| 6 | Type coercion | "true" → True, "8000" → 8000 automatically |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ValidationError: DATABASE_URL field required` | No `.env` file or variable missing | `cp .env.example .env` |
| `Literal['ollama','groq','openai'] expected` | Typo in LLM_PROVIDER value | Fix the value in `.env` to one of the 3 options |
| `Settings object is not subscriptable` | Using `settings["KEY"]` instead of `settings.KEY` | Use dot notation: `settings.DATABASE_URL` |
| `@lru_cache` not working | Function called with different arguments each time | `get_settings()` has no arguments — cache key is empty tuple |

---

## Try It Yourself

```bash
cd backend
source venv/bin/activate

# Quick test — verify config loads:
python -c "
from app.config import get_settings
s = get_settings()
print(f'App: {s.APP_NAME}')
print(f'Env: {s.APP_ENV}')
print(f'LLM: {s.LLM_PROVIDER}')
print(f'DB:  {s.DATABASE_URL.split(\"@\")[-1]}')  # Print host only, not password
"
# Expected:
# App: Health Tracker
# Env: development
# LLM: ollama
# DB:  localhost:5432/healthtracker
```

---

## 🎤 Interview Q&A

### Q: "How do you handle configuration in your application?"

> "Pydantic Settings — a single `Settings` class that reads ALL environment variables from a `.env` file, validates their types, and provides sensible defaults. If a required variable is missing, the app fails at startup with a clear error — fail fast. The Settings object is cached with `@lru_cache` so the `.env` file is read once and the result is reused throughout the application's lifetime. I use `Literal` types to restrict certain fields to valid values — for example, `LLM_PROVIDER` can only be 'ollama', 'groq', or 'openai'. This catches misconfigurations at startup, not at 3 AM in production."

### Q: "What is @lru_cache and why do you use it?"

> "LRU cache is a decorator that memorizes a function's return value. The first call executes the function and caches the result. Subsequent calls with the same arguments return the cached result instantly. I use it on `get_settings()` because Settings initialization reads the `.env` file from disk — an I/O operation. Since environment variables don't change at runtime, there's no reason to re-read the file on every call. The cache means `get_settings()` runs once (at startup) and returns the same object for the rest of the process's lifetime."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 02c — Dockerfile](./phase4-part02c-dockerfile-backend.md) | | [Part 02e — database.py](./phase4-part02e-database.md) |
