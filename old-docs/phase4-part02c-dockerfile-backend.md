# Phase 4 — Part 02c: Backend Dockerfile (Multi-Stage Build)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 02c |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.1 — FastAPI Foundation |
| **File** | `backend/Dockerfile` |
| **Depends On** | Part 02a (requirements.txt — installed during build) |
| **Next** | [Part 02d — config.py](./phase4-part02d-config.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~12 minutes |
| **Lines** | ~65 lines |

---

## What is a Dockerfile? Read This First

A Dockerfile is a **recipe** for building a Docker image. Each line is an instruction:

```dockerfile
FROM python:3.11-slim    # Start with Python 3.11 (the base ingredient)
COPY requirements.txt .  # Copy your shopping list into the kitchen
RUN pip install ...      # Install all ingredients
COPY . .                 # Copy your recipe (source code)
CMD ["uvicorn", ...]     # The command to start cooking (run the server)
```

When you run `docker build`, Docker follows this recipe and creates an **image** — a snapshot of the OS + your code + all dependencies. When you run `docker run`, it creates a **container** — a running instance of that image.

**Analogy:**
- Dockerfile = recipe
- Docker image = prepared meal kit (everything pre-measured and packed)
- Docker container = the meal being cooked and served

### What is Multi-Stage Build?

A regular Dockerfile installs EVERYTHING in one layer — build tools, dev dependencies, the actual app. The resulting image is huge (~500MB).

A multi-stage build uses MULTIPLE `FROM` statements:
- Stage 1 (builder): Install dependencies with build tools (~500MB)
- Stage 2 (production): Copy ONLY the installed packages and code (~150MB)

The final image doesn't include gcc, build tools, or dev dependencies. Smaller = faster deploys, smaller attack surface.

```
Single stage:  500MB image (includes gcc, pip cache, dev tools)
Multi-stage:   150MB image (only runtime + your code)
```

---

## Source Code — Line by Line

> 📁 **File:** `backend/Dockerfile`
> 📏 **Lines:** ~65
> ⏱️ **Type time:** ~12 minutes

### Stage 1: Builder

```dockerfile
# ── Stage 1: Builder ──
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
```

**Line-by-line:**
- **`FROM python:3.11-slim AS builder`** — Start from an official Python image. `slim` = minimal OS (~150MB vs ~900MB for the full image). `AS builder` = name this stage (referenced later).
- **`WORKDIR /build`** — All subsequent commands run in `/build` directory.
- **`apt-get install gcc libpq-dev`** — `gcc` = C compiler (needed to build some Python packages). `libpq-dev` = PostgreSQL client headers (needed for psycopg2).
- **`rm -rf /var/lib/apt/lists/*`** — Delete apt cache after install. Reduces image size by ~30MB.
- **`COPY requirements.txt .`** — Copy ONLY requirements.txt first. Docker caches layers. If requirements.txt hasn't changed, this layer is reused (fast rebuilds!).
- **`--prefix=/install`** — Install packages to a separate directory (not the system Python). We'll copy ONLY this directory to the final image.

### Stage 2: Development

```dockerfile
# ── Stage 2: Development ──
FROM python:3.11-slim AS development

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Key lines:**
- **`COPY --from=builder /install /usr/local`** — Copy the installed packages from Stage 1 into this image. The builder stage is thrown away.
- **`requirements-dev.txt`** — Also install dev tools (pytest, ruff, mypy) in the dev image.
- **`--reload`** — Uvicorn watches for file changes and auto-restarts (development only).

### Stage 3: Production

```dockerfile
# ── Stage 3: Production ──
FROM python:3.11-slim AS production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# SECURITY: Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=builder /install /usr/local

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

USER appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
```

**Key lines:**
- **`RUN addgroup ... adduser`** — Create a non-root user. Production containers should NEVER run as root. If an attacker exploits the app, they get `appuser` privileges (limited), not `root` (full control).
- **`COPY app/ ./app/`** — Copy ONLY the application code (no tests, no dev files). Smaller image, smaller attack surface.
- **`USER appuser`** — Switch to the non-root user. All subsequent commands run as this user.
- **`gunicorn -w 4`** — Gunicorn manages 4 uvicorn workers. If one crashes, gunicorn restarts it. Production-grade process management.
- **`-k uvicorn.workers.UvicornWorker`** — Use uvicorn's async worker class inside gunicorn. Best of both: gunicorn's process management + uvicorn's async handling.

---

## How This Connects

```
Dockerfile
  │
  ├── docker-compose.yml references it:
  │     build:
  │       context: ./backend
  │       dockerfile: Dockerfile
  │
  ├── docker-compose.dev.yml overrides:
  │     target: development    ← uses Stage 2
  │
  ├── Production deploy uses:
  │     target: production     ← uses Stage 3
  │
  └── CI/CD builds it:
        docker build -t health-tracker-backend ./backend
```

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | Dockerfile | Recipe for building Docker images |
| 2 | Multi-stage build | 3 stages: builder → development → production. Smaller final image |
| 3 | Layer caching | Copy requirements.txt FIRST → cached if unchanged → fast rebuilds |
| 4 | Non-root user | Production containers never run as root (security) |
| 5 | Gunicorn + Uvicorn | Gunicorn = process manager, Uvicorn = async worker. Together = production-grade |
| 6 | `--prefix=/install` | Install to separate dir, copy to final image (skip build tools) |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `gcc: not found` during pip install | Missing C compiler in builder stage | Add `apt-get install gcc` |
| `libpq.so.5: cannot open shared object file` | Missing PostgreSQL runtime library | Add `apt-get install libpq5` in final stage |
| `Permission denied` when writing files | Running as non-root user | Ensure `WORKDIR` is writable, or `chown appuser` |
| Build is slow (5+ minutes) | requirements.txt changed → no cache | Move `COPY requirements.txt` before `COPY . .` for caching |

---

## 🎤 Interview Q&A

### Q: "Explain your Dockerfile"

> "It's a 3-stage multi-stage build. Stage 1 (builder) installs Python dependencies with gcc and build tools — this is ~500MB but only used during build. Stage 2 (development) copies the installed packages, adds dev tools (pytest, ruff), and runs uvicorn with hot reload. Stage 3 (production) copies only the installed packages and application code — no tests, no dev tools. It runs as a non-root user for security, and uses gunicorn with 4 uvicorn workers for production-grade process management. The final production image is ~150MB instead of 500MB."

### Q: "Why multi-stage and not a single stage?"

> "Three reasons. First, image size — the builder stage has gcc, build headers, and pip cache (~350MB of overhead). The production stage only has runtime libraries (~30MB). Second, security — fewer tools in the image means smaller attack surface. If an attacker gets shell access, there's no gcc to compile exploits. Third, build speed — Docker caches each stage. If only my app code changes (not requirements.txt), the builder stage is cached and the build takes 10 seconds instead of 2 minutes."

### Q: "Why gunicorn with uvicorn workers?"

> "Gunicorn is a process manager — it spawns worker processes, restarts them if they crash, handles graceful shutdown. Uvicorn is an async ASGI server — it handles async Python efficiently. Using `-k uvicorn.workers.UvicornWorker`, gunicorn manages multiple uvicorn processes. With 4 workers, I handle 4x the concurrent requests. If one worker crashes on an unhandled exception, gunicorn restarts it without downtime. In development, I use plain uvicorn with --reload for simplicity."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 02b — pyproject.toml](./phase4-part02b-pyproject-toml.md) | | [Part 02d — config.py](./phase4-part02d-config.md) |
