# 🐳 Phase 6 Part 01: Docker Deep Dive

> **"One multi-stage Dockerfile (builder → development → production) producing a 150MB image with a non-root user. Three docker-compose files: production (8 services), dev override (hot reload), and test (tmpfs PostgreSQL). A Makefile with 16 shortcut commands. Plus .env.example and .dockerignore."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 6 — Containerization |
| **Previous** | [Phase 5 Part 03: Integration Tests](./phase5-part03-integration-tests.md) |
| **Next** | [Phase 7: CI/CD Pipeline](./phase7-part01-cicd-github-actions.md) |
| **Files in This Doc** | 7 files (Dockerfile, 3 compose files, Makefile, .env.example, .dockerignore) |
| **Time to Type** | ~50 minutes |
| **Difficulty** | Medium (multi-stage builds, service dependencies, volume mounts) |

---

## 1. `backend/Dockerfile` — Multi-Stage Build

### Type This Code:

```dockerfile
# ============================================================================
# Health Tracker Backend — Multi-Stage Dockerfile
# ============================================================================
# Stage 1 (builder): Install all dependencies — this layer is big (~500MB)
# Stage 2 (development): Used for local dev — has dev tools + hot reload
# Stage 3 (production): Copy only what's needed — small, secure final image
# ============================================================================

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

# Copy application code only (no tests, no dev files)
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

USER appuser

EXPOSE 8000

# Production server: gunicorn with uvicorn workers
CMD ["gunicorn", "app.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
```

### Why Multi-Stage?

```
Stage 1 (builder):     ~500 MB — gcc, libpq-dev, pip packages
Stage 2 (development): ~400 MB — builder packages + dev tools + all source
Stage 3 (production):  ~150 MB — builder packages + app code only

Production image has: NO gcc, NO pytest, NO tests, NO .git
→ Smaller image = faster deploys + smaller attack surface
```

### Key Details

**`COPY requirements.txt .` before `COPY . .`** — Docker layer caching. If requirements.txt hasn't changed, Docker reuses the cached pip install layer (~2 min saved). Only code changes trigger a rebuild of the final `COPY . .` layer.

**`--prefix=/install`** — Installs packages into a separate directory. Stage 3 copies ONLY this directory (`COPY --from=builder /install /usr/local`), leaving behind the build tools.

**`USER appuser`** — The container runs as a non-root user. If an attacker exploits a vulnerability, they get limited permissions — can't install packages, can't read `/etc/shadow`, can't modify system files.

**`gunicorn -w 4 -k uvicorn.workers.UvicornWorker`** — Gunicorn manages 4 worker processes. Each worker runs uvicorn (async). If one worker crashes, gunicorn restarts it. This is the production standard for FastAPI.

---

## 2. `docker-compose.yml` — Production-Like (8 Services)

### Type This Code:

```yaml
# ============================================================================
# Health Tracker — Docker Compose (Production-like)
# ============================================================================

services:
  # ── Reverse Proxy ──
  nginx:
    image: nginx:1.25-alpine
    container_name: ht-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

  # ── Backend API ──
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ht-backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://healthuser:healthpass@postgres:5432/healthtracker
      - DATABASE_URL_SYNC=postgresql://healthuser:healthpass@postgres:5432/healthtracker
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_BASE_URL=http://ollama:11434
      - S3_ENDPOINT=http://minio:9000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  # ── Celery Worker ──
  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ht-celery-worker
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://healthuser:healthpass@postgres:5432/healthtracker
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_BASE_URL=http://ollama:11434
      - S3_ENDPOINT=http://minio:9000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # ── Celery Beat ──
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ht-celery-beat
    command: celery -A app.tasks.celery_app beat --loglevel=info
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://healthuser:healthpass@postgres:5432/healthtracker
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

  # ── PostgreSQL + pgvector ──
  postgres:
    image: pgvector/pgvector:pg16
    container_name: ht-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: healthtracker
      POSTGRES_USER: healthuser
      POSTGRES_PASSWORD: healthpass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U healthuser -d healthtracker"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ── Redis ──
  redis:
    image: redis:7-alpine
    container_name: ht-redis
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ── MinIO (S3-compatible storage) ──
  minio:
    image: minio/minio
    container_name: ht-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # ── Ollama (Local LLM) ──
  ollama:
    image: ollama/ollama
    container_name: ht-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  postgres_data:
    name: ht-postgres-data
  redis_data:
    name: ht-redis-data
  minio_data:
    name: ht-minio-data
  ollama_data:
    name: ht-ollama-data
```

### Service Architecture

```
Browser → :80 → Nginx → :8000 → Backend (FastAPI)
                                      │
                                      ├── :5432 → PostgreSQL + pgvector
                                      ├── :6379 → Redis (cache + Celery broker)
                                      ├── :9000 → MinIO (S3-compatible storage)
                                      └── :11434 → Ollama (local LLM)

              Celery Worker ──→ Redis (broker) ──→ PostgreSQL
              Celery Beat ────→ Redis (scheduler)
```

### Key: Health Checks + Dependency Order

```yaml
depends_on:
  postgres:
    condition: service_healthy    # Wait until PostgreSQL is READY, not just started
```

Without `service_healthy`, the backend starts before PostgreSQL finishes initialization → connection error → crash. Health checks ensure services start in the right order.

### Key: `environment` Overrides `env_file`

```yaml
env_file:
  - .env                          # Base config from file
environment:
  - DATABASE_URL=...@postgres:... # Override: use Docker service name, not localhost
```

The `.env` file has `DATABASE_URL=...@localhost:5432/...` (for running outside Docker). The `environment` section overrides this with `@postgres:5432` — the Docker network service name. Inside Docker, services refer to each other by service name, not `localhost`.

---

## 3. `docker-compose.dev.yml` — Development Override

### Type This Code:

```yaml
# ============================================================================
# Health Tracker — Docker Compose Development Override
# ============================================================================
# Usage: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./backend/app:/app/app:rw
      - ./backend/tests:/app/tests:rw
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  celery-worker:
    profiles:
      - celery

  celery-beat:
    profiles:
      - celery

  nginx:
    profiles:
      - nginx
```

**`target: development`** — Uses stage 2 of the Dockerfile (with dev tools).

**Volume mounts:** `./backend/app:/app/app:rw` — Your local `app/` folder is mounted INTO the container. When you edit a file locally, uvicorn's `--reload` detects the change and restarts the server. No rebuild needed.

**`profiles: [celery]`** — These services are HIDDEN by default in dev. They only start with `docker-compose --profile celery up`. In development, you don't usually need background workers running.

---

## 4. `docker-compose.test.yml` — Test Database

### Type This Code:

```yaml
# ============================================================================
# Health Tracker — Docker Compose for Testing
# ============================================================================

services:
  postgres-test:
    image: pgvector/pgvector:pg16
    container_name: ht-postgres-test
    ports:
      - "5433:5432"
    environment:
      POSTGRES_DB: healthtracker_test
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d healthtracker_test"]
      interval: 5s
      timeout: 3s
      retries: 5
    tmpfs:
      - /var/lib/postgresql/data

  redis-test:
    image: redis:7-alpine
    container_name: ht-redis-test
    ports:
      - "6380:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```

**`port: "5433:5432"`** — Maps to port 5433 on the host so it doesn't conflict with the dev database on 5432.

**`tmpfs: /var/lib/postgresql/data`** — PostgreSQL data stored in RAM, not disk. Tests run faster (~2x) and data is automatically wiped when the container stops. Perfect for tests — you never want test data persisting.

---

## 5. `Makefile` — 16 Shortcut Commands

### Type This Code:

```makefile
.PHONY: help dev up down logs test test-unit test-int lint migrate seed build clean

help:
	@echo "Available commands:"
	@echo "  make dev        - Start development environment"
	@echo "  make up         - Start production-like environment"
	@echo "  make down       - Stop all services"
	@echo "  make test       - Run all tests"
	@echo "  make test-unit  - Run unit tests only"
	@echo "  make test-int   - Run integration tests only"
	@echo "  make lint       - Run linters"
	@echo "  make migrate    - Run database migrations"
	@echo "  make build      - Build Docker images"
	@echo "  make clean      - Remove containers + volumes"

dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

test: test-up
	cd backend && python -m pytest -v --tb=short
	$(MAKE) test-down

test-unit:
	cd backend && python -m pytest tests/unit -v --tb=short

test-int: test-up
	cd backend && python -m pytest tests/integration -v --tb=short
	$(MAKE) test-down

test-up:
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for test databases..."
	@powershell -Command "Start-Sleep -Seconds 5"

test-down:
	docker-compose -f docker-compose.test.yml down

lint:
	cd backend && python -m ruff check app/
	cd backend && python -m mypy app/

format:
	cd backend && python -m ruff format app/

migrate:
	cd backend && python -m alembic upgrade head

seed:
	cd backend && python -m scripts.seed_data

build:
	docker-compose build --no-cache

clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

shell:
	docker-compose exec backend /bin/bash

setup-ollama:
	docker-compose exec ollama ollama pull llama3.1:8b
	docker-compose exec ollama ollama pull nomic-embed-text
```

**`.PHONY`** — Tells Make these are commands, not file names. Without it, if a file called `test` existed, `make test` wouldn't run.

**`$(MAKE) test-down`** — Calls another Make target. Ensures the test database is stopped even if tests fail.

---

## 6. `.env.example` — Environment Variables Template

### Type This Code:

```bash
# ── Database ──
DATABASE_URL=postgresql+asyncpg://healthuser:healthpass@localhost:5432/healthtracker
DATABASE_URL_SYNC=postgresql://healthuser:healthpass@localhost:5432/healthtracker

# ── Redis ──
REDIS_URL=redis://localhost:6379/0

# ── Security ──
SECRET_KEY=change-me-to-a-random-secret-key-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── LLM Provider ──
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
GROQ_API_KEY=
OPENAI_API_KEY=

# ── Embedding Model ──
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# ── Object Storage (S3-compatible) ──
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=health-tracker
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1

# ── Email ──
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
```

---

## 7. `.dockerignore` — Exclude From Build Context

```
.git
.gitignore
.env
.env.*
*.md
docs/
LICENSE
__pycache__
*.pyc
.pytest_cache
.mypy_cache
htmlcov
.coverage
venv
.venv
node_modules
frontend/node_modules
.vscode
.idea
docker-compose*.yml
Dockerfile*
.DS_Store
Thumbs.db
```

**Why it matters:** Without `.dockerignore`, `docker build` copies the entire project directory into the build context (including `.git` at 100MB+, `node_modules`, etc.). Build time goes from 30s to 5+ minutes.

---

## 8. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **Multi-stage Dockerfile** | builder → dev → prod (150MB vs 500MB) |
| 2 | **Layer caching** | COPY requirements.txt before COPY . |
| 3 | **Non-root user** | `USER appuser` in production stage |
| 4 | **gunicorn + uvicorn workers** | Production: process manager + async workers |
| 5 | **Health checks** | `service_healthy` ensures correct startup order |
| 6 | **Service name networking** | `@postgres:5432` inside Docker (not localhost) |
| 7 | **Volume mounts** | Dev: local files → container for hot reload |
| 8 | **`tmpfs`** | Test DB in RAM for speed + auto-cleanup |
| 9 | **Docker profiles** | Hide celery/nginx in dev mode |
| 10 | **`.dockerignore`** | Exclude .git, node_modules from build context |

---

## 9. Interview Questions

### Q1: "Why multi-stage Docker builds?"

**A:** Three benefits: (1) **Smaller image** — production image is ~150MB instead of ~500MB because build tools (gcc, pip, pytest) aren't included. Smaller images mean faster deploys and less storage cost. (2) **Security** — fewer tools in the image means a smaller attack surface. No compiler means an attacker can't build exploits inside the container. (3) **Same Dockerfile** — one file for dev (stage 2 with hot reload) and production (stage 3 with gunicorn). No separate Dockerfiles to maintain.

### Q2: "How does your app handle container orchestration?"

**A:** Docker Compose handles orchestration locally with health checks and dependency ordering. In production, we'd use ECS (Fargate) or Kubernetes. The compose file maps directly to ECS task definitions — each service becomes a container in a task. Health checks transfer as-is to ALB target group health checks. The transition from compose to ECS is mostly config translation, not code changes.

### Q3: "Why separate compose files instead of one big file?"

**A:** Separation of concerns. `docker-compose.yml` defines the production architecture. `docker-compose.dev.yml` overrides specific settings for development (hot reload, debug mode, no nginx). `docker-compose.test.yml` is completely independent — only starts the minimum services needed for tests (PostgreSQL + Redis on different ports). You combine them: `docker-compose -f base.yml -f dev.yml up`. This is the standard Docker Compose override pattern.

---

## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 5 Part 03: Integration Tests](./phase5-part03-integration-tests.md) |
| ➡️ Next | [Phase 7: CI/CD Pipeline](./phase7-part01-cicd-github-actions.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**🎉 Phase 6 (Docker) is COMPLETE.**

*One Dockerfile, three compose files, 8 services, 16 Make commands. Development with hot reload, testing with in-memory databases, production with non-root users and gunicorn. Next: the CI/CD pipeline that automates lint → test → build on every push.*
