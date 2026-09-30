# 🚀 Phase 8 Part 01: Deployment — Local Development

> **"Start the entire stack with one command: `make dev`. PostgreSQL + pgvector, Redis, MinIO, Ollama, FastAPI with hot reload. Then seed data, pull LLM models, and verify all 8 services are running."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 8 — Deployment |
| **Previous** | [Phase 7: CI/CD Pipeline](./phase7-part01-cicd-github-actions.md) |
| **Next** | [Phase 8 Part 02: Staging (Free Tier)](./phase8-part02-deployment-staging-free.md) |

---

## 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | 4.x+ | [docker.com/products/docker-desktop](https://docker.com/products/docker-desktop) |
| Git | 2.x+ | Comes with most OS installs |
| Python | 3.11+ | Only needed for running tests outside Docker |
| Node.js | 20+ | Only needed for frontend development |

**Docker Desktop must be running** — all services run in containers.

---

## 2. Step-by-Step Setup

### Step 1: Clone and Configure

```bash
git clone https://github.com/your-username/health-tracker.git
cd health-tracker

# Create environment file from template
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### Step 2: Start All Services

```bash
# Development mode (hot reload, debug logging)
make dev

# Or explicitly:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This starts 5 services (nginx and celery are hidden in dev via profiles):
| Service | Port | Status Check |
|---------|------|-------------|
| Backend (FastAPI) | :8000 | `curl http://localhost:8000/health` |
| PostgreSQL + pgvector | :5432 | `docker exec ht-postgres pg_isready` |
| Redis | :6379 | `docker exec ht-redis redis-cli ping` |
| MinIO | :9000 (API), :9001 (console) | `http://localhost:9001` (minioadmin/minioadmin) |
| Ollama | :11434 | `curl http://localhost:11434/api/tags` |

### Step 3: Run Database Migrations

```bash
# In another terminal:
make migrate
# Or: cd backend && alembic upgrade head
```

This runs all 5 Alembic migrations: users → habits → habit_logs → AI tables (pgvector) → notification_settings.

### Step 4: Pull LLM Models (First Time Only)

```bash
make setup-ollama
# Or:
docker exec ht-ollama ollama pull llama3.1:8b          # ~4.7 GB
docker exec ht-ollama ollama pull nomic-embed-text      # ~274 MB
```

### Step 5: Seed Sample Data

```bash
make seed
# Creates: 1 test user (shreya@test.com / TestPass123), 6 habits, 90 days of logs
```

### Step 6: Start Frontend (Separate Terminal)

```bash
cd frontend
npm install       # First time only
npm run dev       # Starts on http://localhost:3000
```

### Step 7: Verify Everything

```bash
# Backend health
curl http://localhost:8000/health
# → {"status": "healthy"}

# API docs
open http://localhost:8000/docs    # Swagger UI

# Frontend
open http://localhost:3000         # React app

# Login with seed user
# Email: shreya@test.com
# Password: TestPass123
```

---

## 3. Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Port 5432 already in use | Local PostgreSQL running | Stop it: `sudo systemctl stop postgresql` or change port in compose |
| Ollama OOM killed | Not enough RAM | Reduce model: use `llama3.2:1b` instead of `llama3.1:8b` |
| Backend can't connect to DB | Migrations not run | Run `make migrate` |
| Frontend CORS error | Backend not running | Start backend first, frontend proxy connects to `:8000` |
| `pgvector` extension error | Wrong PostgreSQL image | Must use `pgvector/pgvector:pg16`, not standard `postgres:16` |

---

## 4. Daily Development Workflow

```bash
# Morning: start services
make dev

# Code: edit backend/app/ — uvicorn auto-reloads
# Code: edit frontend/src/ — Vite auto-reloads

# Test: run unit tests (no DB needed)
make test-unit

# Test: run integration tests
make test-int

# Evening: stop everything
make down
```

---

## 5. Navigation

| ⬅️ Previous | [Phase 7: CI/CD](./phase7-part01-cicd-github-actions.md) |
| ➡️ Next | [Phase 8 Part 02: Staging (Free Tier)](./phase8-part02-deployment-staging-free.md) |

---

**End of Phase 8 Part 01: Local Deployment**
