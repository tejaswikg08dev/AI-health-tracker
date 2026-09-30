# Phase 4 — Part 01a: Environment Variables (.env.example)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 01a |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.0 — Project Skeleton |
| **File** | `.env.example` |
| **Depends On** | None (first file!) |
| **Next** | [Part 01b — .gitignore](./phase4-part01b-gitignore.md) |
| **Difficulty** | 🟢 Easy |
| **Time to Type** | ~8 minutes |
| **Lines** | ~40 lines |

---

## What is .env.example? Read This First

Every application needs **configuration** — database URLs, API keys, secret keys. These change between environments:

```
Development:  DATABASE_URL = postgresql://user:pass@localhost:5432/healthtracker
Staging:      DATABASE_URL = postgresql://user:pass@staging-db.render.com:5432/healthtracker
Production:   DATABASE_URL = postgresql://user:pass@prod-rds.amazonaws.com:5432/healthtracker
```

If you hardcode these in Python files, you need to change code for every environment. Instead, we store them in a `.env` file that Python reads at startup.

`.env.example` is the **template** — it shows what variables exist, with fake values. You copy it to `.env` and fill in real values. `.env` is NEVER committed to Git (it's in `.gitignore`).

**Real-world analogy:** `.env.example` is like a form template. `.env` is your filled-in form with your actual answers. You share the template, not your answers.

---

## Architecture: Where This File Fits

```
.env.example ──copy──► .env ──read by──► app/config.py ──used by──► entire app
  (template)           (real secrets)     (Pydantic Settings)
  (committed to Git)   (NEVER committed)  (validates at startup)
```

---

## Source Code — Line by Line

> 📁 **File:** `.env.example`
> 📏 **Lines:** ~40
> ⏱️ **Type time:** ~8 minutes

Type this EXACTLY:

```bash
# ============================================================================
# HEALTH TRACKER — Environment Variables
# ============================================================================
# Copy this file to .env and fill in your values:
#   cp .env.example .env
#
# IMPORTANT: Never commit .env to git. It contains secrets.
# ============================================================================

# ── Database (PostgreSQL + pgvector) ──
DATABASE_URL=postgresql+asyncpg://healthuser:healthpass@localhost:5432/healthtracker
# Sync URL needed by Alembic migrations (asyncpg doesn't work with Alembic CLI)
DATABASE_URL_SYNC=postgresql://healthuser:healthpass@localhost:5432/healthtracker

# ── Redis ──
REDIS_URL=redis://localhost:6379/0

# ── Security ──
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=change-me-to-a-random-secret-key-in-production
# JWT token expiry (minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── LLM Provider ──
# Options: ollama (free, local), groq (free, cloud), openai (paid, production)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
# Groq (free tier: 30 req/min) — get key at https://console.groq.com
GROQ_API_KEY=
# OpenAI (paid) — only for production
OPENAI_API_KEY=

# ── Embedding Model ──
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# ── Object Storage (S3-compatible) ──
# Local dev: MinIO | Production: AWS S3
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=health-tracker
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1

# ── Email ──
# Options: console (dev: prints to terminal), resend (free tier), ses (AWS production)
EMAIL_PROVIDER=console
RESEND_API_KEY=
SES_FROM_EMAIL=noreply@healthtracker.app

# ── CORS ──
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ── App Settings ──
APP_NAME=Health Tracker
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# ── AWS (for Lambda functions) ──
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
SQS_EXPORT_QUEUE_URL=
SQS_STREAK_QUEUE_URL=
```

**Line-by-line explanation:**

- **Lines 1-8:** Comments explaining the file. The `cp` command copies the template to a real `.env`.

- **Line 11:** `DATABASE_URL` — the connection string for PostgreSQL.
  - `postgresql+asyncpg://` — use the asyncpg driver (fast, async)
  - `healthuser:healthpass` — username:password
  - `@localhost:5432` — host:port (Docker exposes PostgreSQL on 5432)
  - `/healthtracker` — database name

- **Line 13:** `DATABASE_URL_SYNC` — same but with `postgresql://` (sync psycopg2 driver). Alembic migrations can't use async drivers, so they need this.

- **Line 16:** `REDIS_URL` — Redis connection. `/0` means database 0 (Redis has 16 databases, 0-15).

- **Line 19:** `SECRET_KEY` — used to sign JWT tokens. If someone knows this key, they can forge tokens for any user. In production, generate a random 32-character string.

- **Line 21-22:** Token expiry times. Access token = 30 minutes (short, limits damage if stolen). Refresh token = 7 days (long, so users don't re-login constantly).

- **Line 25-31:** LLM configuration. `LLM_PROVIDER=ollama` means use the free local AI. Change to `groq` or `openai` to switch providers — zero code changes.

- **Line 37-41:** S3 configuration. MinIO runs locally as an S3 clone. Same `boto3` API works with both MinIO and real AWS S3 — only the endpoint URL changes.

- **Line 44:** `EMAIL_PROVIDER=console` — in development, emails are printed to the terminal instead of actually sent. Change to `resend` or `ses` for real emails.

---

## How This Connects

```
.env.example
     │
     │ cp .env.example .env
     ▼
.env (your real secrets — NEVER committed to Git)
     │
     │ read by Pydantic Settings at startup
     ▼
app/config.py → Settings class
     │
     │ imported by every module
     ▼
database.py (DATABASE_URL)
redis_client.py (REDIS_URL)
security.py (SECRET_KEY)
llm/factory.py (LLM_PROVIDER)
storage.py (S3_ENDPOINT, S3_BUCKET)
email_provider.py (EMAIL_PROVIDER)
```

**Incoming:** You create this file manually.
**Outgoing:** `config.py` reads it via Pydantic Settings.

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | Environment variables | Configuration outside code — changes per environment |
| 2 | .env vs .env.example | Template (committed) vs real secrets (never committed) |
| 3 | Connection strings | `protocol://user:pass@host:port/database` format |
| 4 | Two DB URLs | Async (asyncpg) for app, sync (psycopg2) for migrations |
| 5 | Provider configs | LLM_PROVIDER, EMAIL_PROVIDER — swap via config, not code |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ValidationError: DATABASE_URL field required` | No `.env` file | `cp .env.example .env` |
| `connection refused` | Docker not running | Start Docker Desktop, then `docker-compose up postgres redis -d` |
| `FATAL: password authentication failed` | Wrong password in .env | Match password with docker-compose.yml `POSTGRES_PASSWORD` |
| JWT tokens always invalid | `SECRET_KEY` changed between requests | Don't change SECRET_KEY while users have active tokens |

---

## Try It Yourself

```bash
# 1. Type the file (or copy it as your first exception)
# 2. Create your real .env:
cp .env.example .env

# 3. Verify it exists and .gitignore will catch it:
ls -la .env          # Should exist
cat .gitignore       # Should contain ".env" (we'll create this next)
```

---

## 🎤 Interview Q&A

### Q: "How do you manage configuration across environments?"

> "Environment variables, read by Pydantic Settings at startup. I provide a `.env.example` template in Git with placeholder values. Each environment (dev, staging, production) has its own `.env` with real values. Pydantic validates all variables at startup — if a required variable is missing, the app fails immediately with a clear error instead of crashing later. In production on AWS, secrets come from Secrets Manager and are injected as environment variables by ECS task definitions."

### Q: "What happens if someone accidentally commits a `.env` file?"

> "Two things: First, `.gitignore` prevents this — Git won't track `.env` files. Second, if it does happen (force-add), the secret is compromised. You'd need to: rotate the secret immediately (change database password, generate new JWT secret key), revoke any tokens signed with the old key, and use `git filter-branch` or BFG Repo-Cleaner to purge the file from Git history. This is why we never even add `.env` to staging — it's `.gitignore`d from day one."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 01 Overview](./phase4-part01-project-skeleton-overview.md) | | [Part 01b — .gitignore](./phase4-part01b-gitignore.md) |
