# Phase 4 — Part 01d: Docker Compose Dev Override

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 01d |
| **File** | `docker-compose.dev.yml` |
| **Depends On** | Part 01c (docker-compose.yml — the base) |
| **Next** | [Part 01e — Makefile](./phase4-part01e-makefile.md) |
| **Difficulty** | 🟢 Easy |
| **Time to Type** | ~5 minutes |
| **Lines** | ~25 lines |

---

## What is a Compose Override? Read This First

Docker Compose supports **multiple files** that merge together. The base `docker-compose.yml` defines production-like settings. The `docker-compose.dev.yml` **overrides** specific settings for development.

```bash
# Production-like:
docker-compose up

# Development (merge base + dev overrides):
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**What changes in dev mode?**
- Backend uses `uvicorn --reload` (hot reload — code changes reflect instantly)
- Source code is mounted as a volume (edit file → container sees it immediately)
- Celery and Nginx are disabled (access FastAPI directly on :8000)
- Debug mode enabled

**Real-world analogy:** The base compose is the restaurant's standard setup. The dev override is "training mode" — the kitchen door is propped open (debug), orders go directly to the chef (no Nginx), and the menu updates live (hot reload).

---

## Source Code — Line by Line

> 📁 **File:** `docker-compose.dev.yml`
> 📏 **Lines:** ~25
> ⏱️ **Type time:** ~5 minutes

```yaml
# ============================================================================
# Health Tracker — Docker Compose Development Override
# ============================================================================
# Usage (always combine with base):
#   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
# ============================================================================

services:
  # Override backend to use uvicorn with hot reload
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: development    # Use dev stage of multi-stage Dockerfile
    volumes:
      # Mount source code — changes reflect without rebuilding
      - ./backend/app:/app/app:rw
      - ./backend/tests:/app/tests:rw
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  # Disable celery worker/beat in dev (run manually if needed)
  celery-worker:
    profiles:
      - celery

  celery-beat:
    profiles:
      - celery

  # Disable nginx in dev (access FastAPI directly on :8000)
  nginx:
    profiles:
      - nginx
```

**Key lines:**
- **`target: development`** — Our Dockerfile has 3 stages (builder, development, production). This tells Docker to stop at the `development` stage (has dev tools, no gunicorn).
- **`volumes: ./backend/app:/app/app:rw`** — Mounts your local `app/` folder INTO the container. When you save a file, the container sees the change immediately. `:rw` = read-write.
- **`--reload`** — Uvicorn watches for file changes and auto-restarts. Edit `router.py` → save → server restarts in 1 second.
- **`profiles: celery`** — This service only starts if you explicitly ask: `docker-compose --profile celery up`. By default, it's skipped.

---

## 🎤 Interview Q&A

### Q: "How do you handle dev vs production Docker configs?"

> "Docker Compose supports file merging. My base `docker-compose.yml` defines all services with production-like settings. A `docker-compose.dev.yml` override changes the backend to use uvicorn with hot reload, mounts source code as a volume for instant changes, enables debug logging, and disables Nginx and Celery (access FastAPI directly). The command is: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`. This means the base file is always production-ready, and dev is a thin overlay."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 01c — docker-compose.yml](./phase4-part01c-docker-compose.md) | | [Part 01e — Makefile](./phase4-part01e-makefile.md) |
