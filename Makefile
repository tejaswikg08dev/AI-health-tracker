# ============================================================================
# Health Tracker — Makefile (Shortcut Commands)
# ============================================================================
# Usage: make <command>
#
# WHY a Makefile:
#   Instead of remembering long docker-compose commands, you type:
#     make dev    → starts everything for development
#     make test   → runs all tests
#   Every company uses Makefiles or similar task runners.
# ============================================================================

.PHONY: help dev up down logs test test-unit test-int lint migrate seed build clean

# Show all available commands
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
	@echo "  make shell      - Open a shell in the backend container"

# ── Development ──
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

# ── Testing ──
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

# ── Code Quality ──
lint:
	cd backend && python -m ruff check app/
	cd backend && python -m mypy app/

format:
	cd backend && python -m ruff format app/

# ── Database ──
migrate:
	cd backend && python -m alembic upgrade head

migrate-create:
	@echo "Usage: cd backend && alembic revision --autogenerate -m 'description'"

seed:
	cd backend && python -m scripts.seed_data

# ── Docker ──
build:
	docker-compose build --no-cache

clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# ── Utility ──
shell:
	docker-compose exec backend /bin/bash

# ── Ollama Setup ──
setup-ollama:
	docker-compose exec ollama ollama pull llama3.1:8b
	docker-compose exec ollama ollama pull nomic-embed-text
