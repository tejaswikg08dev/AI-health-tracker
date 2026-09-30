# Phase 4 — Part 01c: Docker Compose (docker-compose.yml)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 01c |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.0 — Project Skeleton |
| **File** | `docker-compose.yml` |
| **Depends On** | Part 01a (.env.example — uses env vars) |
| **Next** | [Part 01d — docker-compose.dev.yml](./phase4-part01d-docker-compose-dev.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~15 minutes |
| **Lines** | ~120 lines |

---

## What is Docker Compose? Read This First

Docker Compose lets you run **multiple Docker containers** with ONE command. Instead of:

```bash
# Without Docker Compose (run each service manually):
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=pass pgvector/pgvector:pg16
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name minio -p 9000:9000 minio/minio server /data
docker run -d --name ollama -p 11434:11434 ollama/ollama
# ...and 3 more services
```

You write a `docker-compose.yml` file and run:

```bash
docker-compose up -d
# ALL 7 services start, connected, with health checks. One command.
```

**Real-world analogy:** Docker Compose is like a restaurant's opening checklist:
1. ✅ Turn on oven (PostgreSQL)
2. ✅ Turn on fridge (Redis)
3. ✅ Open storage room (MinIO)
4. ✅ Start coffee machine (Ollama)
5. ✅ Unlock front door (Nginx)

Instead of doing each manually, one checklist runs everything.

---

## Architecture: What This File Creates

```
┌── docker-compose.yml creates all of this: ──┐
│                                              │
│  ┌──────────┐  ┌───────┐  ┌──────┐         │
│  │PostgreSQL │  │ Redis │  │MinIO │         │
│  │ :5432     │  │ :6379 │  │:9000 │         │
│  │ +pgvector │  │       │  │:9001 │         │
│  └──────────┘  └───────┘  └──────┘         │
│                                              │
│  ┌──────────┐  ┌────────────┐  ┌─────────┐ │
│  │ Ollama   │  │ Backend    │  │  Nginx  │ │
│  │ :11434   │  │ :8000      │  │  :80    │ │
│  │ (LLM)    │  │ (FastAPI)  │  │ (proxy) │ │
│  └──────────┘  └────────────┘  └─────────┘ │
│                                              │
│  ┌────────────┐  ┌────────────┐             │
│  │Celery      │  │Celery Beat │             │
│  │Worker      │  │(Scheduler) │             │
│  └────────────┘  └────────────┘             │
│                                              │
│  All connected on a Docker network.          │
│  Services reference each other by name:      │
│  backend → postgres:5432 (not localhost!)     │
└──────────────────────────────────────────────┘
```

---

## Source Code — Line by Line

> 📁 **File:** `docker-compose.yml`
> 📏 **Lines:** ~120
> ⏱️ **Type time:** ~15 minutes

### Section 1: PostgreSQL + pgvector

```yaml
services:
  # ── PostgreSQL + pgvector ──
  # Primary database: users, habits, logs, analytics, AI documents + embeddings
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
```

**Line-by-line:**
- **`image: pgvector/pgvector:pg16`** — This Docker image has PostgreSQL 16 WITH the pgvector extension pre-installed. Without it, we'd need to install pgvector manually.
- **`container_name: ht-postgres`** — Name for the container (shows in `docker ps`). `ht-` prefix = Health Tracker.
- **`ports: "5432:5432"`** — Maps container port 5432 to your laptop's port 5432. This lets `psql` and SQLAlchemy connect to `localhost:5432`.
- **`environment`** — Creates the database, user, and password automatically on first run.
- **`volumes: postgres_data:/var/lib/...`** — Saves data to a Docker volume. Without this, data is LOST when the container stops.
- **`healthcheck`** — Docker runs `pg_isready` every 10 seconds to verify PostgreSQL is alive. Other services use `condition: service_healthy` to wait for this.
- **`restart: unless-stopped`** — If PostgreSQL crashes, Docker restarts it automatically. Unless YOU stopped it with `docker-compose stop`.

### Section 2: Redis

```yaml
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
```

**Key lines:**
- **`redis:7-alpine`** — Alpine is a tiny Linux (~5MB). Redis on Alpine = ~30MB image vs ~100MB for the full image.
- **`--maxmemory 128mb`** — Redis uses RAM. Cap it at 128MB so it doesn't eat all your laptop's memory.
- **`--maxmemory-policy allkeys-lru`** — When memory is full, delete Least Recently Used keys. This means old cache entries are automatically evicted.
- **`--appendonly yes`** — Persist data to disk. If Redis restarts, data is recovered.

### Section 3: MinIO (S3-compatible storage)

```yaml
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
    restart: unless-stopped
```

**Key lines:**
- **Port 9000** — API port (boto3 connects here)
- **Port 9001** — Web console (visit http://localhost:9001 in browser to see files)
- **`minioadmin/minioadmin`** — Default credentials. These go in your `.env` as `S3_ACCESS_KEY` and `S3_SECRET_KEY`.

### Section 4: Ollama, Backend, Celery, Nginx, Volumes

```yaml
  # ── Ollama (Local LLM) ──
  ollama:
    image: ollama/ollama
    container_name: ht-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
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
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_BASE_URL=http://ollama:11434
      - S3_ENDPOINT=http://minio:9000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # ── Nginx ──
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

volumes:
  postgres_data:
  redis_data:
  minio_data:
  ollama_data:
```

**Critical concept:** Inside Docker Compose, services reference each other by NAME, not `localhost`:
- Backend → `postgres:5432` (not `localhost:5432`)
- Backend → `redis:6379` (not `localhost:6379`)
- Backend → `ollama:11434` (not `localhost:11434`)

That's why the `environment` section overrides DATABASE_URL to use `postgres` as the hostname.

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | Docker Compose | YAML file that defines and runs multi-container applications |
| 2 | Service naming | Containers reference each other by service name (not localhost) |
| 3 | Health checks | Docker verifies services are ready before starting dependents |
| 4 | Volumes | Persistent storage that survives container restarts |
| 5 | Port mapping | `"host:container"` — maps container port to your laptop |
| 6 | env_file | Reads `.env` file and passes variables to the container |
| 7 | depends_on + condition | Start order: PostgreSQL first, then backend |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `port is already allocated` | Another service on port 5432 | Stop local PostgreSQL, or change port to `5433:5432` |
| `no such image: pgvector/pgvector:pg16` | Docker can't pull the image | Check internet connection, run `docker pull pgvector/pgvector:pg16` |
| `connection refused` from backend to postgres | Backend started before PostgreSQL was ready | Add `depends_on: postgres: condition: service_healthy` |
| `volumes: postgres_data: external: true` error | Volume doesn't exist | Remove `external: true` or run `docker volume create postgres_data` |

---

## Try It Yourself

```bash
# Start just the databases (no backend yet — we haven't written it)
docker-compose up postgres redis minio -d

# Verify all three are running
docker-compose ps
# Expected: ht-postgres (healthy), ht-redis (healthy), ht-minio (running)

# Test PostgreSQL
docker-compose exec postgres psql -U healthuser -d healthtracker -c "SELECT 1;"
# Expected: ?column? | 1

# Test Redis
docker-compose exec redis redis-cli ping
# Expected: PONG

# Test MinIO console
# Open browser: http://localhost:9001
# Login: minioadmin / minioadmin

# Stop everything
docker-compose down
```

---

## 🎤 Interview Q&A

### Q: "Explain your Docker Compose setup"

> "Seven services: PostgreSQL with pgvector for relational data and vector search, Redis for caching and rate limiting, MinIO as a local S3-compatible store, Ollama for free local AI, the FastAPI backend, a Celery worker for background tasks, and Nginx as a reverse proxy. All services have health checks — the backend won't start until PostgreSQL and Redis report healthy. Data persists across restarts via named volumes. The key insight is that inside the Docker network, services use hostnames (postgres, redis) not localhost."

### Q: "Why is pgvector bundled with PostgreSQL?"

> "We use the `pgvector/pgvector:pg16` image which pre-installs the pgvector extension. This means I can `CREATE EXTENSION vector` and immediately store 768-dimensional embedding vectors alongside my regular relational data. No separate vector database to manage. The alternative — running Pinecone alongside PostgreSQL — adds cost ($70/month), complexity (two databases to backup), and breaks transactional guarantees (document insert and chunk insert can't be atomic)."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 01b — .gitignore](./phase4-part01b-gitignore.md) | | [Part 01d — docker-compose.dev.yml](./phase4-part01d-docker-compose-dev.md) |
