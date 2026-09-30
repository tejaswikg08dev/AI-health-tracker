# 📚 CORRECTED Naming Convention & Doc Structure

## PayFlow Pattern vs My Wrong Pattern

### PayFlow's ACTUAL Pattern (what we must follow):

```
phase4-part07-merchant-service-overview.md     ← MODULE overview
phase4-part07a-merchant-project-setup.md       ← setup (pom.xml, yml, main class)
phase4-part07b-merchant-entities.md            ← all entities in ONE doc
phase4-part07c-merchant-migrations.md          ← all migrations in ONE doc
phase4-part07d-merchant-repositories.md        ← all repos in ONE doc
phase4-part07e-merchant-dtos-mapper.md         ← all DTOs + mappers in ONE doc
phase4-part07f-merchant-services-tests.md      ← all services + tests in ONE doc
phase4-part07g-merchant-controller-docker.md   ← controller + docker in ONE doc
phase4-part07h-merchant-connections-and-flows.md ← architecture diagrams
```

### Key Differences:
1. **Config files (env, gitignore, docker-compose) go in ONE doc** — not separate docs each
2. **Each module gets 4-8 sub-parts** — not 12+
3. **Related files are grouped** — entities.md has ALL models, not one doc per model
4. **Part numbers are for MODULES** — part04=Auth, part05=Habits, part06=Logs...

---

## CORRECTED Complete File List

### Phase 0: Overview & Setup (2 docs — like PayFlow)

```
phase0-part1-project-overview.md              ← Project vision, features, architecture, tech stack, timeline
phase0-part2-environment-setup.md             ← Python, Docker, Node.js, VS Code — step by step with troubleshooting
```

### Phase 1-3: Design (3 docs — like PayFlow)

```
phase1-system-design.md                        ← Requirements, design decisions (boxed format), API design, DB design, capacity planning
phase2-high-level-design.md                    ← Component diagrams, data flows, deployment
phase3-low-level-design.md                     ← Entity signatures, repository interfaces, service methods, SQL migrations
```

### Phase 4: Implementation (numbered by module, sub-parts by layer)

```
── Sprint 1: Foundation + Auth ──

phase4-part01-project-setup-docker.md          ← .env, .gitignore, docker-compose.yml, dev/test overrides, Makefile, Dockerfile — ALL in ONE doc
phase4-part02-backend-foundation.md            ← requirements.txt, pyproject.toml, config.py, database.py, redis_client.py, dependencies.py — ALL in ONE doc
phase4-part03-shared-utilities-middleware.md    ← ALL shared/ files + ALL middleware/ files — ONE doc

phase4-part04-auth-service-overview.md         ← Auth module overview & roadmap (PayFlow style)
phase4-part04a-auth-entities-schemas.md        ← models.py + exceptions.py + schemas.py (all "data shape" files)
phase4-part04b-auth-security-jwt.md            ← security.py (bcrypt + JWT deep dive)
phase4-part04c-auth-repository-service.md      ← repository.py + service.py (data access + business logic)
phase4-part04d-auth-controller-main-nginx.md   ← router.py + main.py + nginx/default.conf (HTTP layer + wiring)
phase4-part04e-auth-alembic-migrations.md      ← alembic.ini + env.py + 001_create_users_table.py
phase4-part04f-auth-connections-and-flows.md    ← Sequence diagrams: signup, login, refresh, logout flows

── Sprint 2: Core Tracking ──

phase4-part05-habits-service-overview.md        ← Habits module overview & roadmap
phase4-part05a-habits-entities-migrations.md    ← models.py + exceptions.py + schemas.py + migration
phase4-part05b-habits-repositories.md           ← repository.py
phase4-part05c-habits-service-tests.md          ← service.py
phase4-part05d-habits-controller-docker.md      ← router.py + register in main.py
phase4-part05e-habits-connections-and-flows.md   ← Flow diagrams

phase4-part06-logs-service-overview.md          ← Logs module overview
phase4-part06a-logs-entities-migrations.md
phase4-part06b-logs-repository-service.md
phase4-part06c-logs-controller.md
phase4-part06d-logs-connections-and-flows.md

phase4-part07-analytics-service-overview.md     ← Analytics module overview
phase4-part07a-analytics-schemas.md
phase4-part07b-analytics-repository-sql.md      ← ⭐⭐ THE BIG SQL FILE
phase4-part07c-analytics-cache-service.md       ← Redis cache + Pearson correlation
phase4-part07d-analytics-controller.md
phase4-part07e-analytics-connections-and-flows.md

phase4-part07f-seed-data.md                     ← scripts/seed_data.py

── Sprint 3: AI Module ──

phase4-part08-ai-llm-overview.md                ← LLM layer overview
phase4-part08a-ai-llm-base-client.md            ← base_client.py (Strategy pattern) ⭐⭐
phase4-part08b-ai-llm-providers.md              ← ollama + groq + openai + factory (3 clients + factory in ONE doc)
phase4-part08c-ai-llm-prompts-tokens.md         ← prompt_templates.py + token_tracker.py

phase4-part09-ai-rag-overview.md                ← RAG pipeline overview
phase4-part09a-ai-rag-ingestion.md              ← document_processor.py + chunker.py + embeddings.py
phase4-part09b-ai-rag-retrieval.md              ← vector_store.py + retriever.py ⭐⭐
phase4-part09c-ai-rag-connections-and-flows.md   ← Full RAG flow diagram

phase4-part10-ai-agents-overview.md             ← Agents overview
phase4-part10a-ai-agent-tools.md                ← base_tool.py + ALL 5 tools in ONE doc
phase4-part10b-ai-agent-memory.md               ← short_term.py + long_term.py
phase4-part10c-ai-agent-react-loop.md           ← base_agent.py + health_coach.py ⭐⭐⭐
phase4-part10d-ai-agent-connections-and-flows.md ← Full agent execution trace

phase4-part11-ai-workflows-overview.md          ← Workflows overview
phase4-part11a-ai-workflow-pipeline.md           ← base_workflow.py + orchestrator.py + 3 steps
phase4-part11b-ai-workflow-connections-and-flows.md

phase4-part12-ai-service-router-overview.md     ← AI wiring overview
phase4-part12a-ai-models-schemas.md             ← models.py + schemas.py (4 tables + request/response)
phase4-part12b-ai-service-router.md             ← service.py + router.py (9 endpoints)
phase4-part12c-ai-migration.md                  ← 004_create_ai_tables.py
phase4-part12d-ai-complete-architecture.md       ← Complete AI module connections

── Sprint 4: Delivery + Lambda ──

phase4-part13-notifications-service-overview.md
phase4-part13a-notifications-entities-schemas.md
phase4-part13b-notifications-email-provider.md
phase4-part13c-notifications-service-tasks-controller.md
phase4-part13d-notifications-templates-migration.md
phase4-part13e-notifications-connections-and-flows.md

phase4-part14-export-service-overview.md
phase4-part14a-export-csv-pdf-storage.md
phase4-part14b-export-service-controller.md
phase4-part14c-export-connections-and-flows.md

phase4-part15-lambda-overview.md
phase4-part15a-lambda-shared-sam-template.md
phase4-part15b-lambda-scheduled-functions.md     ← daily_reminder + weekly_report + data_cleanup
phase4-part15c-lambda-event-driven-functions.md  ← csv_export + streak_milestone + document_processor
phase4-part15d-lambda-connections-and-flows.md

── Sprint 5: Frontend + Tests + Deploy ──

phase4-part16-frontend-overview.md
phase4-part16a-frontend-setup-types.md           ← config files + all 7 type files
phase4-part16b-frontend-api-layer.md             ← api.ts + all 7 service files
phase4-part16c-frontend-state-hooks.md           ← auth-store + all 5 hooks + utils
phase4-part16d-frontend-layout-routing.md        ← main.tsx + App.tsx + layout components
phase4-part16e-frontend-auth-pages.md            ← Login + Signup
phase4-part16f-frontend-core-pages.md            ← Dashboard + Habits + CheckIn
phase4-part16g-frontend-analytics-chat-pages.md  ← Analytics + Chat + Settings
phase4-part16h-frontend-components.md            ← HabitCard, HabitForm, DailyCheckIn, Charts, ChatWindow
phase4-part16i-frontend-connections-and-flows.md

── Phase 5-10 ──

phase5-part01-testing-overview.md
phase5-part02-test-infrastructure.md             ← conftest + factories + mocks
phase5-part03-unit-tests.md                      ← ALL unit tests
phase5-part04-integration-tests.md               ← ALL integration tests

phase6-part01-docker-deep-dive.md                ← ALL Docker: Dockerfile, compose, networking

phase7-part01-cicd-github-actions.md             ← CI/CD pipeline

phase8-part01-deployment-local.md
phase8-part02-deployment-staging.md
phase8-part03-deployment-aws-production.md

phase9-part01-nginx-monitoring.md

phase10-part01-e2e-curl-commands.md
phase10-part02-interview-prep.md                 ← ALL interview Q&A in ONE doc
```

---

## CORRECTED Count

| Section | Docs | Was (wrong) |
|---------|------|-------------|
| Phase 0 | 2 | 5 (too many) |
| Phase 1-3 | 3 | 4 |
| Phase 4 Sprint 1 | 10 (1+1+1 + 7 auth) | 28 (too granular) |
| Phase 4 Sprint 2 | 16 | same |
| Phase 4 Sprint 3 | 19 | same |
| Phase 4 Sprint 4 | 12 | same |
| Phase 4 Sprint 5 | 10 | same |
| Phase 5-10 | 11 | 17 (too many) |
| **TOTAL** | **~83 docs** | 154 (way too many!) |

The PayFlow project has ~115 docs for a 12-microservice Java project.
Our project should have **~80-85 docs** for a 7-module Python project.

The key change: **grouping related files into ONE doc** instead of one doc per file.

---

## Doc Size at PayFlow Quality

| Doc Type | Estimated Size |
|----------|---------------|
| Phase 0 overview | ~2,000-3,000 lines each |
| System Design | ~3,000-5,000 lines |
| HLD / LLD | ~1,500-2,500 lines each |
| Module overview (partNN) | ~500-1,000 lines |
| Implementation sub-part (partNNa-f) | ~1,000-3,000 lines |
| Connections-and-flows | ~500-1,000 lines |

**Total estimated: ~150,000-200,000 lines of documentation**

---

## Ready to Start Fresh?

Say "start fresh" and I'll:
1. Delete ALL existing incorrectly named/structured docs
2. Create `phase0-part1-project-overview.md` at PayFlow quality (~2,000+ lines)
3. Continue doc by doc in the corrected order
