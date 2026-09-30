# Phase 4 — Part 01e: Makefile — Shortcut Commands

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 01e |
| **File** | `Makefile` |
| **Depends On** | Part 01c-d (docker-compose files — Makefile runs them) |
| **Next** | [Part 02 Overview — FastAPI Foundation](./phase4-part02-fastapi-foundation-overview.md) |
| **Difficulty** | 🟢 Easy |
| **Time to Type** | ~8 minutes |
| **Lines** | ~55 lines |

---

## What is a Makefile? Read This First

A Makefile defines **shortcut commands**. Instead of typing a long command:

```bash
# Without Makefile (every time):
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# With Makefile:
make dev
```

**Real-world analogy:** Speed dial on your phone. Instead of typing a 10-digit number, you press "1" for Mom. Makefile is speed dial for terminal commands.

Make originated from C/C++ compilation but is now used as a general-purpose task runner. It works on Mac, Linux, and Windows (with Git Bash).

---

## Source Code — Line by Line

> 📁 **File:** `Makefile`
> 📏 **Lines:** ~55
> ⏱️ **Type time:** ~8 minutes

```makefile
# ============================================================================
# Health Tracker — Makefile (Shortcut Commands)
# ============================================================================

.PHONY: help dev up down logs test test-unit test-int lint migrate seed build clean

help:
	@echo "Available commands:"
	@echo "  make dev        - Start development environment (hot reload)"
	@echo "  make up         - Start production-like environment"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - Follow all container logs"
	@echo "  make test       - Run all tests"
	@echo "  make test-unit  - Run unit tests only"
	@echo "  make test-int   - Run integration tests only"
	@echo "  make lint       - Run linters (ruff + mypy)"
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed database with sample data"
	@echo "  make build      - Build Docker images"
	@echo "  make clean      - Remove containers, volumes, and cached files"

dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	cd backend && python -m pytest -v --tb=short

test-unit:
	cd backend && python -m pytest tests/unit -v --tb=short

test-int:
	cd backend && python -m pytest tests/integration -v --tb=short

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

**Key lines:**
- **`.PHONY`** — Tells Make these are commands, not files. Without it, if a file named `test` exists, `make test` would skip (thinking the "file" is already built).
- **`@echo`** — The `@` suppresses Make from printing the command itself. Without it, you'd see both the echo command and its output.
- **`make dev`** — The command you'll use every day. Starts everything in dev mode.
- **`make clean`** — Nuclear option. Stops containers, removes volumes (deletes ALL data), prunes unused images. Use when things are really broken.

**IMPORTANT:** Makefiles use TABS, not spaces, for indentation. If you use spaces, you'll get `Makefile:4: *** missing separator. Stop.` This is the #1 Makefile error.

---

## 🎤 Interview Q&A

### Q: "How do you standardize development commands across a team?"

> "A Makefile at the project root. `make dev` starts everything, `make test` runs all tests, `make lint` checks code quality, `make migrate` runs database migrations. Every developer runs the same commands regardless of OS. It also serves as documentation — `make help` lists all available commands. For more complex workflows, I'd consider a Taskfile (YAML-based) or just-runner, but Make is universal and has zero dependencies."

---

## ✅ Sprint 1 Release 1.0 Complete!

You've typed all 5 skeleton files. Before moving on, verify:

```bash
cp .env.example .env
docker-compose up postgres redis -d
docker-compose ps          # Both healthy?
docker-compose exec redis redis-cli ping  # PONG?
make help                  # Shows commands?
```

If all pass → move to [Part 02 — FastAPI Foundation](./phase4-part02-fastapi-foundation-overview.md) 🚀

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 01d — docker-compose.dev.yml](./phase4-part01d-docker-compose-dev.md) | | [Part 02 Overview — FastAPI Foundation](./phase4-part02-fastapi-foundation-overview.md) |
