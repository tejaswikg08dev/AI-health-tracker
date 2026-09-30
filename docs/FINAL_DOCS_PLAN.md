# 📚 FINAL Documentation Plan — Python/FastAPI Naming

## Our Project's Layer Names (NOT Spring Boot)

| Spring Boot (PayFlow) | Python/FastAPI (Our Project) |
|----------------------|------------------------------|
| entities | models (SQLAlchemy models) |
| DTOs + Mappers | schemas (Pydantic schemas) |
| JPA repositories | repositories (SQLAlchemy queries) |
| services | services (business logic) |
| controllers | routers (FastAPI routers) |
| application.yml | config.py (Pydantic Settings) |
| pom.xml / Gradle | requirements.txt / pyproject.toml |
| Flyway migrations | Alembic migrations |
| Spring Security | security.py (bcrypt + JWT manual) |
| @Entity | class User(Base) with mapped_column |
| @Repository | class UserRepository(BaseRepository[User]) |
| @Service | class AuthService |
| @RestController | router = APIRouter() |
| @Autowired | Depends() |
| SecurityFilterChain | middleware (rate_limiter, error_handler) |
| Eureka / Config Server | N/A (modular monolith, no service discovery) |
| Kafka | Celery + Redis (background tasks) |
| Feign | direct service import (same process) |

---

## FINAL Corrected File List (~80 docs)

### Phase 0: Overview & Setup (2 docs)

```
phase0-part1-project-overview.md
  What we build, features, architecture diagram, tech stack, timeline, interview pitch

phase0-part2-environment-setup.md
  Python 3.11, Docker Desktop, Node.js 20, Git, VS Code
  Step-by-step with screenshots, verification commands, 20+ troubleshooting errors
```

### Phase 1-3: Design (3 docs)

```
phase1-system-design.md
  Requirements (functional + non-functional), 10+ design decisions (boxed format),
  API design (38 endpoints with request/response examples),
  database design (8 tables with full CREATE TABLE SQL),
  capacity planning with math, security design, AI pipeline design

phase2-high-level-design.md
  Full architecture diagram, component responsibilities, 5 data flow traces,
  module dependency map, technology choice rationale table, scaling strategy

phase3-low-level-design.md
  All SQLAlchemy model class signatures, all repository method signatures,
  all service method signatures, all router endpoint signatures,
  Alembic migration summary, streak algorithm, cache-aside pattern,
  ReAct agent loop pseudocode, RAG pipeline steps
```

### Phase 4: Implementation

```
── Sprint 1: Foundation + Auth ──

phase4-part01-project-setup-docker.md
  .env.example (full file + line-by-line)
  .gitignore (full file + explanation)
  docker-compose.yml (full file + every service explained)
  docker-compose.dev.yml (full file)
  docker-compose.test.yml (full file)
  Makefile (full file + every command)
  .dockerignore (full file)

phase4-part02-backend-foundation.md
  requirements.txt (full file + every package explained)
  pyproject.toml (full file + every tool config)
  Dockerfile (full file + multi-stage explained)
  app/__init__.py
  app/config.py (full file + Pydantic Settings deep dive)
  app/database.py (full file + async SQLAlchemy + connection pool)
  app/redis_client.py (full file + Redis use cases)
  app/dependencies.py (full file + FastAPI Depends + Annotated)

phase4-part03-shared-utilities-middleware.md
  shared/__init__.py
  shared/exceptions.py (full file + exception hierarchy)
  shared/base_schemas.py (full file + Generic[T] + @property)
  shared/base_repository.py (full file + TypeVar + CRUD)
  shared/date_utils.py (full file + timezone handling)
  shared/logging.py (full file + structlog)
  middleware/__init__.py
  middleware/error_handler.py (full file + 4 handler functions)
  middleware/logging_middleware.py (full file + request_id)
  middleware/rate_limiter.py (full file + Redis sliding window)

phase4-part04-auth-module-overview.md
  What auth does, JWT flow diagram, token lifecycle,
  real-world analogy, tech stack (bcrypt, JWT NEW),
  6 endpoints table, build order, file list, prerequisites,
  verification checklist, navigation to sub-parts

phase4-part04a-auth-models-schemas.md
  modules/auth/__init__.py
  modules/auth/models.py (User model — full file + every column explained)
  modules/auth/exceptions.py (5 auth errors — full file)
  modules/auth/schemas.py (UserCreate, TokenResponse — full file)

phase4-part04b-auth-security-jwt.md
  modules/auth/security.py — FULL FILE + deep dive:
    bcrypt: how hashing works, cost factor, salt
    JWT: header.payload.signature, HS256, access vs refresh
    create_access_token, create_refresh_token, decode_token

phase4-part04c-auth-repository-service.md
  modules/auth/repository.py (UserRepository — full file)
  modules/auth/service.py (AuthService — full file + every method)
    register flow, login flow, refresh flow, logout flow, token blacklist

phase4-part04d-auth-router-main-nginx.md
  modules/auth/router.py (6 endpoints — full file)
  app/main.py (app factory, lifespan, middleware, routers — full file)
  nginx/default.conf (reverse proxy, rate limiting, SSE — full file)

phase4-part04e-auth-alembic-migrations.md
  alembic.ini (full file)
  alembic/env.py (full file + model imports)
  alembic/script.py.mako (template)
  alembic/versions/001_create_users_table.py (full file)

phase4-part04f-auth-connections-and-flows.md
  Signup sequence diagram (step by step)
  Login sequence diagram
  Token refresh sequence diagram
  Logout + blacklist flow
  Complete architecture: how auth connects to everything

── Sprint 2: Core Tracking ──

phase4-part05-habits-module-overview.md
phase4-part05a-habits-models-schemas-migration.md
  models.py + exceptions.py + schemas.py + 002_migration — ALL full files
phase4-part05b-habits-repository-service.md
  repository.py + service.py — full files
phase4-part05c-habits-router.md
  router.py + register in main.py — full files
phase4-part05d-habits-connections-and-flows.md

phase4-part06-logs-module-overview.md
phase4-part06a-logs-models-schemas-migration.md
phase4-part06b-logs-repository-service.md
phase4-part06c-logs-router.md
phase4-part06d-logs-connections-and-flows.md

phase4-part07-analytics-module-overview.md
phase4-part07a-analytics-schemas.md
phase4-part07b-analytics-repository-sql.md       ← ⭐⭐ Window functions, CTEs
phase4-part07c-analytics-cache-service.md         ← ⭐ Cache-aside + Pearson
phase4-part07d-analytics-router.md
phase4-part07e-analytics-connections-and-flows.md
phase4-part07f-seed-data.md

── Sprint 3: AI Module ──

phase4-part08-ai-llm-overview.md
phase4-part08a-ai-llm-base-client.md              ← ⭐⭐ Strategy pattern
phase4-part08b-ai-llm-providers-factory.md         ← Ollama + Groq + OpenAI + factory
phase4-part08c-ai-llm-prompts-tokens.md

phase4-part09-ai-rag-overview.md
phase4-part09a-ai-rag-ingestion.md                 ← PDF extract + chunk + embed
phase4-part09b-ai-rag-retrieval.md                 ← ⭐⭐ pgvector + retriever
phase4-part09c-ai-rag-connections-and-flows.md

phase4-part10-ai-agents-overview.md
phase4-part10a-ai-agent-tools.md                   ← base_tool + 5 tools
phase4-part10b-ai-agent-memory.md                  ← short_term + long_term
phase4-part10c-ai-agent-react-loop.md              ← ⭐⭐⭐ base_agent + health_coach
phase4-part10d-ai-agent-connections-and-flows.md

phase4-part11-ai-workflows-overview.md
phase4-part11a-ai-workflow-pipeline.md             ← orchestrator + 3 steps
phase4-part11b-ai-workflow-connections-and-flows.md

phase4-part12-ai-service-router-overview.md
phase4-part12a-ai-models-schemas.md
phase4-part12b-ai-service-router.md
phase4-part12c-ai-migration.md
phase4-part12d-ai-complete-architecture.md

── Sprint 4: Delivery + Lambda ──

phase4-part13-notifications-module-overview.md
phase4-part13a-notifications-models-schemas-email-provider.md
phase4-part13b-notifications-service-tasks-router.md
phase4-part13c-notifications-templates-migration.md
phase4-part13d-notifications-connections-and-flows.md

phase4-part14-export-module-overview.md
phase4-part14a-export-csv-pdf-storage.md
phase4-part14b-export-service-router.md
phase4-part14c-export-connections-and-flows.md

phase4-part15-lambda-overview.md
phase4-part15a-lambda-shared-sam-template.md
phase4-part15b-lambda-scheduled-functions.md
phase4-part15c-lambda-event-driven-functions.md
phase4-part15d-lambda-connections-and-flows.md

── Sprint 5: Frontend + Tests ──

phase4-part16-frontend-overview.md
phase4-part16a-frontend-setup-types.md
phase4-part16b-frontend-api-layer.md
phase4-part16c-frontend-state-hooks.md
phase4-part16d-frontend-layout-routing.md
phase4-part16e-frontend-pages.md
phase4-part16f-frontend-components-charts.md
phase4-part16g-frontend-connections-and-flows.md
```

### Phase 5-10

```
phase5-part01-testing-overview-infrastructure.md
phase5-part02-unit-tests.md
phase5-part03-integration-tests.md

phase6-part01-docker-deep-dive.md

phase7-part01-cicd-github-actions.md

phase8-part01-deployment-local.md
phase8-part02-deployment-staging-free.md
phase8-part03-deployment-aws-production.md
phase8-part04-deployment-lambda.md

phase9-part01-nginx-monitoring.md

phase10-part01-e2e-curl-commands.md
phase10-part02-interview-prep-complete.md
```

---

## Naming Convention Rules

### Pattern
```
phase{N}-part{NN}-{python-fastapi-description}.md           ← Module overview
phase{N}-part{NN}{letter}-{python-fastapi-description}.md    ← Sub-part
```

### Python/FastAPI Terms Used (NOT Spring Boot)

| Use This | NOT This |
|----------|----------|
| `models` | ~~entities~~ |
| `schemas` | ~~dtos-mapper~~ |
| `repository` | ~~jpa-repositories~~ |
| `service` | ~~services-tests~~ |
| `router` | ~~controller~~ |
| `config` | ~~application-yml~~ |
| `alembic-migrations` | ~~flyway-migrations~~ |
| `security-jwt` | ~~spring-security~~ |
| `base-client` | ~~interface~~ |
| `factory` | ~~bean-configuration~~ |
| `middleware` | ~~filter-chain~~ |
| `dependencies` | ~~autowired~~ |
| `pydantic-settings` | ~~spring-cloud-config~~ |
| `celery-tasks` | ~~kafka-consumers~~ |
| `react-pages` | ~~thymeleaf-templates~~ |

### Description Naming Rules
- Use Python/FastAPI terminology
- Kebab-case: `auth-security-jwt`, `analytics-repository-sql`
- Group by layer: `models-schemas`, `repository-service`, `router`
- Module name first: `auth-models-schemas`, `habits-repository-service`

---

## Final Count

| Section | Docs |
|---------|------|
| Phase 0 | 2 |
| Phase 1-3 | 3 |
| Phase 4 Sprint 1 | 10 |
| Phase 4 Sprint 2 | 16 |
| Phase 4 Sprint 3 | 16 |
| Phase 4 Sprint 4 | 12 |
| Phase 4 Sprint 5 | 8 |
| Phase 5-10 | 12 |
| **TOTAL** | **~79 docs** |

Each doc at PayFlow quality level: 1,000-5,000 lines
Estimated total: ~150,000-200,000 lines of documentation

---

## Ready?

Say **"start fresh"** and I will:
1. Delete ALL old incorrectly named docs
2. Start with `phase0-part1-project-overview.md` at full PayFlow quality
3. Use Python/FastAPI terminology throughout
4. Group files properly (not one doc per file)
5. Include FULL source code in every doc
