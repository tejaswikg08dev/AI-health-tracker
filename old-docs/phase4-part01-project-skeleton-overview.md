# 🏗️ Phase 4 Part 01: Project Skeleton — Overview & Roadmap

> **"Every great building starts with digging the foundation. Every great project starts with the right folder structure and config."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Health Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 01 (split into 01a through 01e) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.0 — Project Skeleton |
| **Files in this group** | 5 files |
| **Endpoints** | 0 (no code yet — just config) |
| **Database tables** | 0 (created later in Part 04) |
| **Total typing time** | ~40 minutes |
| **Previous** | [Phase 3 Part 02 — Database Design](./phase3-part02-database-design.md) |
| **Next** | [Phase 4 Part 02 — FastAPI Foundation](./phase4-part02-fastapi-foundation-overview.md) |

---

## 🎯 What Is the Project Skeleton?

Before writing any Python or React code, you need the **infrastructure**:
- Environment variables (secrets, database URLs, API keys)
- Docker Compose (PostgreSQL, Redis, MinIO, Ollama — all running with one command)
- Development vs production overrides
- Shortcut commands (Makefile)

### Real-World Analogy

| Step | Building a Restaurant | Building This Project |
|------|----------------------|----------------------|
| 1 | Rent a space, connect electricity + water | `.env` — configure database URLs, API keys |
| 2 | Decide what goes where (kitchen, dining, bar) | `docker-compose.yml` — which services, which ports |
| 3 | Open doors for employees but not customers yet | `docker-compose.dev.yml` — development mode |
| 4 | Write a checklist for daily opening procedure | `Makefile` — shortcut commands for common tasks |
| 5 | Put up a "Do Not Enter" sign on the kitchen | `.gitignore` — files that should never be shared |

---

## 🛠️ Tech Stack

| Technology | Purpose | NEW? |
|-----------|---------|------|
| **Docker** | Run PostgreSQL, Redis, MinIO, Ollama in containers | 🆕 **NEW** |
| **Docker Compose** | Orchestrate 7+ containers with one command | 🆕 **NEW** |
| **Make** | Shortcut commands (like npm scripts but language-agnostic) | 🆕 **NEW** |
| **Environment variables** | Store secrets outside code | 🆕 **NEW** |

---

## 📄 Sub-Parts — Build Order (01a → 01e)

```
┌──────────────────────────────────────────────────────────┐
│                    BUILD ORDER                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  01a  .env.example          What environment vars exist  │
│   ▼                                                      │
│  01b  .gitignore            What files to never commit   │
│   ▼                                                      │
│  01c  docker-compose.yml    7 services definition        │
│   ▼                                                      │
│  01d  docker-compose.dev.yml Development overrides       │
│   ▼                                                      │
│  01e  Makefile              Shortcut commands             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**No dependencies between these files** — you can type them in any order. But the order above makes the most sense for understanding.

---

## 🗂️ Complete File List (5 files)

```
health-tracker/
├── .env.example              ← 01a  (template for environment variables)
├── .env                      ← (copy of .env.example — NEVER committed)
├── .gitignore                ← 01b  (files Git ignores)
├── docker-compose.yml        ← 01c  (7 services: postgres, redis, minio, ollama, backend, celery, nginx)
├── docker-compose.dev.yml    ← 01d  (dev overrides: hot reload, debug, skip celery/nginx)
├── docker-compose.test.yml   ← (bonus: test-only services on different ports)
└── Makefile                  ← 01e  (12 shortcut commands)
```

---

## 🔐 Key Concepts

### Environment Variables — Why Not Hardcode Secrets?

```python
# ❌ NEVER DO THIS (secret in code → committed to Git → leaked)
DATABASE_URL = "postgresql://admin:SuperSecretPassword@localhost:5432/mydb"

# ✅ DO THIS (secret in .env file → .gitignore → never committed)
import os
DATABASE_URL = os.environ.get("DATABASE_URL")
```

If you hardcode a database password and push to GitHub, bots scan public repos and find it within MINUTES. Real-world incidents: companies have had their AWS accounts drained of thousands of dollars because someone committed an AWS key.

### Docker Compose — Why Not Install PostgreSQL Directly?

```
WITHOUT Docker:
  1. Download PostgreSQL installer (200MB)
  2. Run installer, choose options, set password
  3. It installs system-wide (conflicts with other versions)
  4. Teammate on Mac does different steps
  5. Three months later: "works on my machine, breaks on yours"

WITH Docker Compose:
  1. docker-compose up -d postgres
  2. PostgreSQL 16 is running on port 5432
  3. Same version on every machine
  4. docker-compose down → everything cleaned up
```

---

## ✅ Prerequisites

Before typing these files, you need:
- [ ] Docker Desktop installed and running (Phase 0, Part 04)
- [ ] A terminal open in the `health-tracker/` folder
- [ ] A text editor (VS Code recommended)

---

## ✅ Verification Checklist (After All 5 Sub-Parts)

After typing all 5 files, run these commands:

```bash
# 1. Copy env template
cp .env.example .env

# 2. Start databases
docker-compose up postgres redis -d

# 3. Verify PostgreSQL is running
docker-compose ps
# Expected: ht-postgres ... healthy

# 4. Verify Redis is running
docker-compose exec redis redis-cli ping
# Expected: PONG

# 5. Check Make commands work
make help
# Expected: list of available commands
```

If all 5 pass, Part 01 is complete. Move to Part 02.

---

## 🎤 Interview Q&A

### Q: "How do you manage secrets in your project?"

> "Environment variables stored in a `.env` file that's listed in `.gitignore` — never committed to Git. I provide a `.env.example` template with placeholder values and comments explaining each variable. In production, secrets would be stored in AWS Secrets Manager and injected as environment variables by ECS task definitions. The application reads them via Pydantic Settings, which validates types at startup — if a required variable is missing, the app fails immediately with a clear error instead of crashing later with a cryptic message."

### Q: "Why Docker Compose instead of installing services directly?"

> "Reproducibility. Without Docker, every developer installs different PostgreSQL versions, different Redis configs, forgets to create the database. With Docker Compose, `docker-compose up` gives everyone the exact same PostgreSQL 16, Redis 7, and pgvector extension. It also matches production — if it works in Docker locally, it works in ECS Fargate on AWS. Cleanup is one command: `docker-compose down -v`."

---

## 📚 Navigation

| Document | Title |
|----------|-------|
| **This document** | **Project Skeleton — Overview & Roadmap** |
| [Part 01a](./phase4-part01a-env-example.md) | .env.example — Environment Variables |
| [Part 01b](./phase4-part01b-gitignore.md) | .gitignore — What Never Gets Committed |
| [Part 01c](./phase4-part01c-docker-compose.md) | docker-compose.yml — 7 Services |
| [Part 01d](./phase4-part01d-docker-compose-dev.md) | docker-compose.dev.yml — Dev Overrides |
| [Part 01e](./phase4-part01e-makefile.md) | Makefile — Shortcut Commands |

---

*Start with [Part 01a — .env.example](./phase4-part01a-env-example.md) →*
