# 📚 MASTER DOCUMENTATION PLAN — Health Tracker

## The Complete Plan for 173 Documents + 17 Visual HTML Pages

> **"You will type every line of this project by reading ONLY these docs. No guessing, no searching, no YouTube. Each doc has the exact code, exact commands, exact order."**

---

## How This Works

### The Promise
After all docs are generated, you will:
1. Open `phase0-part01-project-overview.md` — read it
2. Open `phase4-part01a-env-example.md` — type the code shown
3. Run the verification command shown at the bottom
4. Move to the next doc (linked in the footer)
5. Repeat until the entire project is built

**You never need to look at the source code files.** The docs ARE the source code with explanations.

### The PayFlow Pattern (What You Showed Me)
Every overview doc (like PayFlow's `phase4-part08-payment-service-overview.md`) has:
- Quote at the top (sets the mood)
- Document metadata table
- "What is this?" with real-world analogy table
- Tech stack table (what's NEW in this group)
- Endpoints table (what we build)
- State machines / flow diagrams (if applicable)
- Architecture diagram (ASCII)
- Build order diagram (sub-parts 8a → 8k)
- Complete file list (every file with which sub-part)
- Key concepts explained (idempotency, two-phase payment, etc.)
- Prerequisites (what must be running)
- Verification checklist (after all sub-parts)
- Navigation table (links to every sub-part)

Every sub-part doc has:
- Metadata table
- "Read This First" concept explanation
- Architecture position diagram
- **EXACT source code** (character for character)
- Line-by-line explanation
- "How This Connects" diagram
- "What You Learned" table
- "Common Errors & Fixes" table
- "Try It Yourself" verification
- Interview question + answer
- Prev/Next navigation footer

---

## 📁 Complete Docs Folder Structure

```
health-tracker/
├── docs/
│   │
│   │ ═══════════════════════════════════════════
│   │ META DOCUMENTS (planning, not tutorials)
│   │ ═══════════════════════════════════════════
│   ├── MASTER_DOCS_PLAN.md          ← THIS FILE (the plan)
│   ├── INDEX.md                     ← Master index with links to all 173 docs
│   ├── BUG-FIX-REPORT.md           ← Bugs found and fixed during doc writing
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 0: OVERVIEW & SETUP (5 docs)
│   │ "Before you write a single line of code"
│   │ ═══════════════════════════════════════════
│   ├── phase0-part01-project-overview.md
│   │     What we're building, who it's for, features list, screenshots
│   │
│   ├── phase0-part02-architecture-overview.md
│   │     Full system diagram, 7 modules explained, data flows, request lifecycle
│   │
│   ├── phase0-part03-tech-stack-explained.md
│   │     Every technology: Python, FastAPI, SQLAlchemy, Redis, Docker, Ollama...
│   │     WHY each was chosen, what alternatives exist, comparison tables
│   │
│   ├── phase0-part04-environment-setup.md
│   │     Step-by-step: install Python, Docker, Node.js, VS Code extensions
│   │     Verify each tool: python --version, docker --version, node --version
│   │     Create project folder, git init
│   │
│   ├── phase0-part05-ai-concepts-from-zero.md
│   │     LLM, tokens, embeddings, vectors, cosine similarity, RAG, agents,
│   │     prompt engineering, chunking, temperature — all explained for a beginner
│   │     with diagrams and analogies
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 1-3: SYSTEM DESIGN (4 docs)
│   │ "Design BEFORE you code"
│   │ ═══════════════════════════════════════════
│   ├── phase1-part01-system-design-overview.md
│   │     7-step system design process applied to this project
│   │     Requirements (functional + non-functional), capacity estimates,
│   │     API design, trade-offs table
│   │
│   ├── phase2-part01-high-level-design.md
│   │     Architecture diagram, component overview, data flows,
│   │     technology choices with rationale
│   │
│   ├── phase3-part01-low-level-design.md
│   │     Auth sequence diagram, streak algorithm, rate limiter design,
│   │     ReAct agent loop, cache-aside pattern
│   │
│   ├── phase3-part02-database-design.md
│   │     ER diagram (8 tables), all indexes, design decisions explained,
│   │     why UUID not auto-increment, why 3 value columns not JSONB
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 4: IMPLEMENTATION (104 docs)
│   │ "Type every line, in this exact order"
│   │ THIS IS 80% OF THE DOCUMENTATION
│   │ ═══════════════════════════════════════════
│   │
│   │ ─── Sprint 1: Foundation + Auth (Week 1) ───
│   │
│   │ RELEASE 1.0: Project Skeleton
│   ├── phase4-part01-project-skeleton-overview.md          ← OVERVIEW: 5 sub-parts
│   │     Quote, what this group does, file list, build order, verification
│   ├── phase4-part01a-env-example.md                       ← .env.example
│   ├── phase4-part01b-gitignore.md                         ← .gitignore
│   ├── phase4-part01c-docker-compose.md                    ← docker-compose.yml
│   ├── phase4-part01d-docker-compose-dev.md                ← docker-compose.dev.yml
│   ├── phase4-part01e-makefile.md                          ← Makefile
│   │
│   │ RELEASE 1.1: FastAPI Foundation
│   ├── phase4-part02-fastapi-foundation-overview.md        ← OVERVIEW: 7 sub-parts
│   │     What infrastructure code is, dependency graph, concepts preview
│   ├── phase4-part02a-requirements.md                      ← requirements.txt
│   ├── phase4-part02b-pyproject-toml.md                    ← pyproject.toml
│   ├── phase4-part02c-dockerfile-backend.md                ← Dockerfile (multi-stage)
│   ├── phase4-part02d-config.md                            ← app/config.py
│   ├── phase4-part02e-database.md                          ← app/database.py
│   ├── phase4-part02f-redis-client.md                      ← app/redis_client.py
│   ├── phase4-part02g-dependencies.md                      ← app/dependencies.py
│   │
│   │ RELEASE 1.2 + 1.3: Shared Utilities + Middleware
│   ├── phase4-part03-shared-and-middleware-overview.md      ← OVERVIEW: 8 sub-parts
│   ├── phase4-part03a-exceptions.md                        ← shared/exceptions.py
│   ├── phase4-part03b-base-schemas.md                      ← shared/base_schemas.py
│   ├── phase4-part03c-base-repository.md                   ← shared/base_repository.py
│   ├── phase4-part03d-date-utils.md                        ← shared/date_utils.py
│   ├── phase4-part03e-logging.md                           ← shared/logging.py
│   ├── phase4-part03f-error-handler.md                     ← middleware/error_handler.py
│   ├── phase4-part03g-logging-middleware.md                 ← middleware/logging_middleware.py
│   ├── phase4-part03h-rate-limiter.md                      ← middleware/rate_limiter.py
│   │
│   │ RELEASE 1.4 + 1.5: Auth Module + Main + Nginx
│   ├── phase4-part04-auth-module-overview.md                ← OVERVIEW: 12 sub-parts
│   │     Quote, real-world analogy (hotel check-in), JWT flow diagram,
│   │     tech stack (bcrypt, JWT NEW), endpoints table, state diagram
│   │     (unauthenticated → registered → logged in → token expired → refreshed),
│   │     architecture diagram, build order (04a→04l), file list (12 files),
│   │     key concepts (bcrypt, JWT, token blacklist, same error for wrong email/password),
│   │     prerequisites (PostgreSQL + Redis running), verification checklist,
│   │     navigation table to all 12 sub-parts
│   ├── phase4-part04a-auth-models.md                       ← auth/models.py
│   ├── phase4-part04b-auth-exceptions.md                   ← auth/exceptions.py
│   ├── phase4-part04c-auth-schemas.md                      ← auth/schemas.py
│   ├── phase4-part04d-auth-security.md                     ← auth/security.py ⭐
│   ├── phase4-part04e-auth-repository.md                   ← auth/repository.py
│   ├── phase4-part04f-auth-service.md                      ← auth/service.py ⭐
│   ├── phase4-part04g-auth-router.md                       ← auth/router.py
│   ├── phase4-part04h-auth-connections-and-flows.md        ← Sequence diagrams: signup, login, refresh, logout
│   ├── phase4-part04i-alembic-setup.md                     ← alembic.ini + env.py
│   ├── phase4-part04j-migration-users.md                   ← 001_create_users_table.py
│   ├── phase4-part04k-main.md                              ← main.py ⭐ (app factory, everything wired)
│   ├── phase4-part04l-nginx.md                             ← nginx/default.conf
│   │
│   │ ─── Sprint 2: Core Tracking (Week 2) ───
│   │
│   │ RELEASE 2.0: Habits Module
│   ├── phase4-part05-habits-module-overview.md              ← OVERVIEW: 8 sub-parts
│   ├── phase4-part05a-habits-models.md                     ← habits/models.py
│   ├── phase4-part05b-habits-exceptions.md                 ← habits/exceptions.py
│   ├── phase4-part05c-habits-schemas.md                    ← habits/schemas.py
│   ├── phase4-part05d-habits-repository.md                 ← habits/repository.py
│   ├── phase4-part05e-habits-service.md                    ← habits/service.py
│   ├── phase4-part05f-habits-router.md                     ← habits/router.py
│   ├── phase4-part05g-habits-migration.md                  ← 002_create_habits_table.py
│   ├── phase4-part05h-habits-connections-and-flows.md      ← Flow diagrams
│   │
│   │ RELEASE 2.1: Logs Module
│   ├── phase4-part06-logs-module-overview.md                ← OVERVIEW: 8 sub-parts
│   ├── phase4-part06a-logs-models.md                       ← logs/models.py
│   ├── phase4-part06b-logs-exceptions.md                   ← logs/exceptions.py
│   ├── phase4-part06c-logs-schemas.md                      ← logs/schemas.py
│   ├── phase4-part06d-logs-repository.md                   ← logs/repository.py
│   ├── phase4-part06e-logs-service.md                      ← logs/service.py ⭐
│   ├── phase4-part06f-logs-router.md                       ← logs/router.py
│   ├── phase4-part06g-logs-migration.md                    ← 003_create_habit_logs_table.py
│   ├── phase4-part06h-logs-connections-and-flows.md        ← Flow diagrams
│   │
│   │ RELEASE 2.2: Analytics Module
│   ├── phase4-part07-analytics-module-overview.md           ← OVERVIEW: 7 sub-parts
│   │     Key concepts: window functions, CTEs, cache-aside, Pearson correlation
│   ├── phase4-part07a-analytics-schemas.md                 ← analytics/schemas.py
│   ├── phase4-part07b-analytics-repository.md              ← analytics/repository.py ⭐⭐
│   ├── phase4-part07c-analytics-cache.md                   ← analytics/cache.py ⭐
│   ├── phase4-part07d-analytics-service.md                 ← analytics/service.py ⭐
│   ├── phase4-part07e-analytics-router.md                  ← analytics/router.py
│   ├── phase4-part07f-analytics-connections-and-flows.md   ← Flow diagrams
│   │
│   │ RELEASE 2.3: Seed Data
│   ├── phase4-part07g-seed-data.md                         ← scripts/seed_data.py
│   │
│   │ ─── Sprint 3: AI Module (Week 3-4) ───
│   │
│   │ RELEASE 3.0: LLM Layer
│   ├── phase4-part08-ai-llm-overview.md                    ← OVERVIEW: 7 sub-parts
│   │     Quote: "The AI module is the brain of Health Tracker"
│   │     What's NEW: Ollama, Groq, OpenAI, httpx, Jinja2, Strategy pattern
│   │     No endpoints yet (infrastructure for AI)
│   │     Key concepts: Strategy pattern, Factory pattern, tokens, temperature
│   ├── phase4-part08a-llm-base-client.md                   ← llm/base_client.py ⭐⭐
│   ├── phase4-part08b-llm-ollama.md                        ← llm/ollama_client.py
│   ├── phase4-part08c-llm-groq.md                          ← llm/groq_client.py
│   ├── phase4-part08d-llm-openai.md                        ← llm/openai_client.py
│   ├── phase4-part08e-llm-factory.md                       ← llm/factory.py
│   ├── phase4-part08f-prompt-templates.md                  ← llm/prompt_templates.py
│   ├── phase4-part08g-token-tracker.md                     ← llm/token_tracker.py
│   │
│   │ RELEASE 3.1: RAG Pipeline
│   ├── phase4-part09-rag-pipeline-overview.md               ← OVERVIEW: 6 sub-parts
│   │     "RAG is how the AI references YOUR documents, not just its training data"
│   │     Pipeline diagram: PDF → extract → chunk → embed → store → retrieve
│   │     Key concepts: embeddings, vector similarity, pgvector, chunking, overlap
│   ├── phase4-part09a-document-processor.md                ← rag/document_processor.py
│   ├── phase4-part09b-chunker.md                           ← rag/chunker.py ⭐
│   ├── phase4-part09c-embeddings.md                        ← rag/embeddings.py
│   ├── phase4-part09d-vector-store.md                      ← rag/vector_store.py ⭐⭐
│   ├── phase4-part09e-retriever.md                         ← rag/retriever.py
│   ├── phase4-part09f-rag-connections-and-flows.md         ← Full RAG flow diagram
│   │
│   │ RELEASE 3.2 + 3.3: Agent Tools + Agent + Memory
│   ├── phase4-part10-agents-overview.md                     ← OVERVIEW: 11 sub-parts
│   │     "An agent doesn't just ANSWER — it THINKS, ACTS, and OBSERVES"
│   │     ReAct loop diagram, 5 tools table, memory types, execution trace example
│   ├── phase4-part10a-base-tool.md                         ← agents/tools/base_tool.py
│   ├── phase4-part10b-tool-query-logs.md                   ← agents/tools/query_logs.py
│   ├── phase4-part10c-tool-get-analytics.md                ← agents/tools/get_analytics.py
│   ├── phase4-part10d-tool-search-docs.md                  ← agents/tools/search_docs.py
│   ├── phase4-part10e-tool-correlate.md                    ← agents/tools/correlate.py
│   ├── phase4-part10f-tool-create-plan.md                  ← agents/tools/create_plan.py
│   ├── phase4-part10g-memory-short-term.md                 ← agents/memory/short_term.py
│   ├── phase4-part10h-memory-long-term.md                  ← agents/memory/long_term.py
│   ├── phase4-part10i-base-agent.md                        ← agents/base_agent.py ⭐⭐⭐
│   ├── phase4-part10j-health-coach.md                      ← agents/health_coach.py ⭐
│   ├── phase4-part10k-agent-connections-and-flows.md       ← Full execution trace
│   │
│   │ RELEASE 3.4: Agentic Workflow
│   ├── phase4-part11-workflows-overview.md                  ← OVERVIEW: 6 sub-parts
│   │     "One agent is good. Three agents in a pipeline are better."
│   │     Pipeline: DataCollector → Analyzer → ReportWriter
│   │     Orchestrator: retry, timeout, fallback
│   ├── phase4-part11a-base-workflow.md                     ← workflows/base_workflow.py
│   ├── phase4-part11b-orchestrator.md                      ← workflows/orchestrator.py ⭐
│   ├── phase4-part11c-data-collector.md                    ← weekly_report/data_collector.py
│   ├── phase4-part11d-analyzer.md                          ← weekly_report/analyzer.py
│   ├── phase4-part11e-report-writer.md                     ← weekly_report/report_writer.py
│   ├── phase4-part11f-workflow-connections-and-flows.md     ← Pipeline execution diagram
│   │
│   │ RELEASE 3.5: AI Service + Router + Migration
│   ├── phase4-part12-ai-service-overview.md                 ← OVERVIEW: 6 sub-parts
│   │     "This wires ALL AI features into the FastAPI app"
│   │     9 endpoints table, architecture showing LLM + RAG + Agent all connected
│   ├── phase4-part12a-ai-models.md                         ← ai/models.py
│   ├── phase4-part12b-ai-schemas.md                        ← ai/schemas.py
│   ├── phase4-part12c-ai-service.md                        ← ai/service.py ⭐⭐
│   ├── phase4-part12d-ai-router.md                         ← ai/router.py
│   ├── phase4-part12e-ai-migration.md                      ← 004_create_ai_tables.py
│   ├── phase4-part12f-ai-complete-connections.md            ← Complete AI architecture
│   │
│   │ ─── Sprint 4: Delivery + Lambda (Week 4) ───
│   │
│   │ RELEASE 4.0: Notifications Module
│   ├── phase4-part13-notifications-overview.md              ← OVERVIEW: 9 sub-parts
│   ├── phase4-part13a-notifications-models.md
│   ├── phase4-part13b-notifications-schemas.md
│   ├── phase4-part13c-email-provider.md
│   ├── phase4-part13d-notifications-service.md
│   ├── phase4-part13e-celery-tasks.md
│   ├── phase4-part13f-notifications-router.md
│   ├── phase4-part13g-email-templates.md
│   ├── phase4-part13h-notification-migration.md
│   │
│   │ RELEASE 4.1: Export Module
│   ├── phase4-part14-export-overview.md                     ← OVERVIEW: 6 sub-parts
│   ├── phase4-part14a-csv-generator.md
│   ├── phase4-part14b-pdf-generator.md
│   ├── phase4-part14c-storage.md                           ← ⭐ S3/MinIO
│   ├── phase4-part14d-export-service.md
│   ├── phase4-part14e-export-router.md
│   ├── phase4-part14f-export-connections-and-flows.md
│   │
│   │ RELEASE 4.2: Lambda Functions
│   ├── phase4-part15-lambda-overview.md                     ← OVERVIEW: 8 sub-parts
│   │     "Serverless: runs ONLY when triggered, costs $0 when idle"
│   │     6 functions table with triggers, SAM template
│   ├── phase4-part15a-lambda-shared.md
│   ├── phase4-part15b-sam-template.md
│   ├── phase4-part15c-lambda-daily-reminder.md
│   ├── phase4-part15d-lambda-weekly-report.md
│   ├── phase4-part15e-lambda-csv-export.md
│   ├── phase4-part15f-lambda-streak-milestone.md            ← ⭐
│   ├── phase4-part15g-lambda-data-cleanup.md
│   ├── phase4-part15h-lambda-document-processor.md
│   │
│   │ ─── Sprint 5: Frontend + Tests + Deploy (Week 5) ───
│   │
│   │ RELEASE 5.0-5.2: Frontend
│   ├── phase4-part16-frontend-overview.md                   ← OVERVIEW: 16 sub-parts
│   │     React + TypeScript crash course, component tree diagram
│   ├── phase4-part16a-frontend-config.md
│   ├── phase4-part16b-typescript-types.md
│   ├── phase4-part16c-api-service.md                       ← ⭐⭐ Axios interceptors
│   ├── phase4-part16d-api-modules.md
│   ├── phase4-part16e-auth-store.md
│   ├── phase4-part16f-hooks.md
│   ├── phase4-part16g-layout.md
│   ├── phase4-part16h-auth-pages.md
│   ├── phase4-part16i-dashboard-page.md
│   ├── phase4-part16j-habits-page.md
│   ├── phase4-part16k-checkin-page.md                      ← ⭐
│   ├── phase4-part16l-analytics-page.md
│   ├── phase4-part16m-chat-page.md                         ← ⭐
│   ├── phase4-part16n-settings-page.md
│   ├── phase4-part16o-components.md
│   ├── phase4-part16p-frontend-connections.md
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 5: TESTING (6 docs)
│   │ ═══════════════════════════════════════════
│   ├── phase5-part01-testing-overview.md
│   ├── phase5-part02-conftest.md
│   ├── phase5-part03-factories-and-mocks.md
│   ├── phase5-part04-unit-tests.md
│   ├── phase5-part05-integration-tests.md
│   ├── phase5-part06-testing-coverage-matrix.md
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 6: DOCKER (3 docs)
│   │ ═══════════════════════════════════════════
│   ├── phase6-part01-docker-deep-dive.md
│   ├── phase6-part02-compose-services.md
│   ├── phase6-part03-docker-networking.md
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 7: CI/CD (2 docs)
│   │ ═══════════════════════════════════════════
│   ├── phase7-part01-cicd-overview.md
│   ├── phase7-part02-github-actions.md
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 8: DEPLOYMENT (4 docs)
│   │ ═══════════════════════════════════════════
│   ├── phase8-part01-local-setup.md
│   ├── phase8-part02-staging-deploy.md
│   ├── phase8-part03-aws-production.md
│   ├── phase8-part04-lambda-deploy.md
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 9: NGINX & MONITORING (2 docs)
│   │ ═══════════════════════════════════════════
│   ├── phase9-part01-nginx-deep-dive.md
│   ├── phase9-part02-monitoring.md
│   │
│   │ ═══════════════════════════════════════════
│   │ PHASE 10: E2E TESTING & INTERVIEW (4 docs)
│   │ ═══════════════════════════════════════════
│   ├── phase10-part01-e2e-curl-commands.md
│   ├── phase10-part02-interview-system-design.md
│   ├── phase10-part03-interview-sql.md
│   ├── phase10-part04-interview-ai-concepts.md
│   │
│   │ ═══════════════════════════════════════════
│   │ EXISTING REFERENCE DOCS (already created)
│   │ ═══════════════════════════════════════════
│   ├── architecture/
│   │   ├── HLD.md
│   │   ├── LLD.md
│   │   ├── ai-architecture.md
│   │   ├── database-design.md
│   │   ├── api-design.md
│   │   └── system-flowchart.md
│   ├── deployment/
│   │   ├── local-setup.md
│   │   ├── staging-deploy.md
│   │   ├── aws-deploy.md
│   │   └── lambda-deploy.md
│   ├── interview-prep/
│   │   ├── system-design-answers.md
│   │   ├── sql-queries.md
│   │   └── ai-concepts.md
│   └── learning-notes/
│       ├── week-1-notes.md
│       ├── week-2-notes.md
│       ├── week-3-notes.md
│       ├── week-4-notes.md
│       └── week-5-notes.md
│
├── visual-docs/                              ← Interactive HTML pages
│   ├── index.html                            ← Dashboard with animated stats
│   ├── architecture.html                     ← Clickable module diagram
│   ├── ai-pipeline-flow.html                 ← Animated agent execution
│   ├── rag-pipeline.html                     ← Animated RAG: PDF → answer
│   ├── api-reference.html                    ← Searchable 38 endpoints
│   ├── database-er.html                      ← 8 tables with column tooltips
│   ├── interview-qa.html                     ← 30 Q&A with difficulty badges
│   ├── flashcards.html                       ← Flip cards with scoring
│   ├── cheat-sheet.html                      ← Printable one-page summary
│   ├── elevator-pitch.html                   ← Timed 2/5/15 min scripts
│   ├── module-deep-dive.html                 ← Per-module detailed view
│   ├── docker-vs-cloud.html                  ← Local vs staging vs prod
│   ├── cost-calculator.html                  ← AWS cost sliders
│   ├── live-demo.html                        ← Simulated user flow
│   ├── project-timeline.html                 ← Scroll-triggered phases
│   ├── agent-simulator.html                  ← Interactive ReAct loop
│   └── sql-playground.html                   ← Query visualizer
```

---

## 📊 Document Count Summary

| Category | Count |
|----------|-------|
| Meta docs (plan, index, bug report) | 3 |
| Phase 0 — Overview & Setup | 5 |
| Phase 1-3 — System Design | 4 |
| **Phase 4 — Implementation** | **104** |
| ├── Overview docs (one per group) | 16 |
| ├── Sub-part docs (one per file) | 78 |
| └── Connections-and-flows docs | 10 |
| Phase 5 — Testing | 6 |
| Phase 6 — Docker | 3 |
| Phase 7 — CI/CD | 2 |
| Phase 8 — Deployment | 4 |
| Phase 9 — Nginx & Monitoring | 2 |
| Phase 10 — E2E & Interview | 4 |
| **Total Markdown Docs** | **137** |
| **Visual HTML Pages** | **17** |
| **Grand Total** | **154 deliverables** |

---

## 🏗️ Overview Doc Template (PayFlow Style)

Every `phase4-partNN-{module}-overview.md` follows this EXACT structure:

```markdown
# 🏗️ Phase 4 Part {NN}: {Module Name} — Overview & Roadmap

> **"{Memorable quote about this module}"**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Health Tracker |
| **Phase** | 4 — Implementation |
| **Part** | {NN} (split into {NN}a through {NN}{last_letter}) |
| **Module** | `{module-name}` |
| **Package** | `backend/app/modules/{module}/` |
| **Database** | {table names or "none — reads only"} |
| **Also Uses** | {Redis, Ollama, S3, etc.} |
| **Previous** | [Phase 4 Part {NN-1}{last} — {prev title}](./{prev_file}) |
| **Next** | [Phase 4 Part {NN+1} — {next title}](./{next_file}) |

---

## 🎯 What Is the {Module}?

{3-4 paragraphs explaining this module. Written for someone who has NEVER 
seen this pattern before. Use a real-world analogy.}

### Real-World Analogy

| Step | Real World | Health Tracker Equivalent |
|------|-----------|--------------------------|
| 1 | {analogy step 1} | {code equivalent} |
| 2 | {analogy step 2} | {code equivalent} |
| ... | ... | ... |

---

## 🛠️ Tech Stack

### What's NEW Compared to Previous Module

| Technology | Purpose | NEW? |
|-----------|---------|------|
| {tech 1} | {what it does} | Same |
| {tech 2} | {what it does} | 🆕 **NEW** |

---

## 📐 What We Build — {N} Endpoints

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | POST | `/{module}` | {description} |
| ... | ... | ... | ... |

---

## 🔄 Key Concepts / State Machines / Flow Diagrams

{Module-specific diagrams. Examples:
- Auth: JWT flow diagram
- Analytics: Cache-aside flow
- AI: ReAct loop diagram
- Logs: Bulk upsert flow}

```
{ASCII diagram}
```

---

## 🏗️ Architecture Diagram

```
{ASCII diagram showing this module's internal architecture
 and how it connects to other modules and infrastructure}
```

---

## 📄 Sub-Parts — Build Order ({NN}a → {NN}{last})

```
{ASCII build order diagram showing dependency flow}
```

---

## 🗂️ Complete File List ({N} files)

```
backend/app/modules/{module}/
├── __init__.py                    ← {NN}a (or implicit)
├── models.py                      ← {NN}a
├── exceptions.py                  ← {NN}b
├── schemas.py                     ← {NN}c
├── repository.py                  ← {NN}d
├── service.py                     ← {NN}e
└── router.py                      ← {NN}f
```

---

## 🔐 Key Concepts Explained

### {Concept 1}
{2-3 paragraphs explaining this concept with code snippets}

### {Concept 2}
{2-3 paragraphs explaining this concept}

---

## ✅ Prerequisites

{What must be running/completed before starting this group}

---

## ✅ Final Verification Checklist (After All Parts)

- [ ] {verification 1}
- [ ] {verification 2}
- [ ] ...

---

## 📚 Navigation

| Document | Title |
|----------|-------|
| **This document** | **{Module} Overview & Roadmap** |
| [Part {NN}a](./{file}) | {title} |
| [Part {NN}b](./{file}) | {title} |
| ... | ... |
| [Part {NN}{last}](./{file}) | Connections & Flows |

---

*Start with [Part {NN}a — {title}](./{file}) →*
```

---

## 📝 Sub-Part Doc Template (PayFlow Style)

Every `phase4-part{NN}{letter}-{name}.md` follows this structure:

```markdown
# Phase 4 — Part {NN}{letter}: {Title}

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | {NN}{letter} |
| **Sprint** | Sprint {X} — {Sprint Name} |
| **Release** | Release {X.Y} — {Release Name} |
| **File** | `{relative/path/to/file.py}` |
| **Depends On** | Part {prev} ({prev_title}) |
| **Next** | Part {next} ({next_title}) |
| **Difficulty** | 🟢 Easy / 🟡 Medium / 🟠 Hard / 🔴 Very Hard |
| **Time to Type** | ~{N} minutes |
| **Lines of Code** | ~{N} lines |

---

## What is {Concept}? Read This First

{2-4 paragraphs for a complete beginner. Real-world analogy.
Explain WHY this exists before HOW it works.}

**Real-world analogy:** {one-liner}

---

## Architecture: Where This File Fits

```
{ASCII diagram showing this file among its neighbors}

     ┌─────────────┐
     │  router.py   │ ← HTTP endpoints
     └──────┬───────┘
            │ calls
     ┌──────▼───────┐
     │  service.py  │ ← Business logic
     └──────┬───────┘
            │ calls
     ┌──────▼───────┐
     │ repository.py│ ← SQL queries
     └──────┬───────┘
            │ queries
     ┌──────▼───────┐
     │  [THIS FILE] │ ← YOU ARE HERE
     └──────────────┘
```

---

## Source Code — Line by Line

> 📁 **File:** `{path}`
> 📏 **Lines:** {N}
> ⏱️ **Type time:** ~{N} minutes

### Section 1: {Imports}

```python
{EXACT code — character for character from the real file}
```

**Line-by-line:**
- **Line 1:** `from datetime import ...` — {explanation}
- **Line 2:** `from sqlalchemy import ...` — {explanation}

### Section 2: {Class/Function definition}

```python
{EXACT code}
```

**Line-by-line:**
- **Line N:** {explanation with WHY, not just WHAT}

{Continue for EVERY section of the file}

---

## How This Connects

```
INCOMING (what calls this file):
  {caller} → calls {function} with {arguments}

OUTGOING (what this file calls):
  {function} → calls {dependency} to {do what}
```

---

## What You Learned

| # | Concept | One-Sentence Summary |
|---|---------|---------------------|
| 1 | {concept} | {summary} |
| 2 | {concept} | {summary} |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `{error message}` | {why} | {how to fix} |

---

## Try It Yourself

```bash
{exact commands to verify this file works}
```

Expected output:
```
{expected result}
```

---

## Interview Question

> **Q:** "{question}"
> **Your answer:** "{prepared answer referencing what you built}"

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part {prev}](./{prev_file}) | | [Part {next}](./{next_file}) |
```

---

## 🚀 How to Generate All Docs

### Option A: Use the DOCUMENTATION_PROMPT.md
1. Open a new AI chat session
2. Paste the content of `docs/DOCUMENTATION_PROMPT.md`
3. Say: "Start with phase0-part01-project-overview.md"
4. After each doc, say: "Next doc please"
5. Save each generated doc to the `docs/` folder

### Option B: Generate in batches
1. "Generate all Phase 0 docs (5 docs)"
2. "Generate Phase 4 Part 01 overview + all sub-parts (6 docs)"
3. "Generate Phase 4 Part 02 overview + all sub-parts (8 docs)"
4. Continue group by group

### Option C: One at a time
1. "Generate phase4-part04-auth-module-overview.md in PayFlow style"
2. "Generate phase4-part04a-auth-models.md with line-by-line code"
3. Continue one at a time

**Estimated generation time:** 2-3 days of prompting (generating ~50 docs/day)

---

## ✅ This Plan Is Complete

| What | Status |
|------|--------|
| Folder structure | ✅ Defined |
| Naming convention | ✅ `phase{N}-part{NN}{letter}-{kebab-name}.md` |
| Overview template (PayFlow style) | ✅ Defined |
| Sub-part template (PayFlow style) | ✅ Defined |
| Complete file list (154 deliverables) | ✅ Listed |
| Difficulty ratings (⭐ system) | ✅ Marked |
| Sprint/Release mapping | ✅ 5 sprints, 12 releases |
| Document count | ✅ 137 markdown + 17 HTML |
| Generation instructions | ✅ 3 options provided |

**Ready to start generating docs? Say "Generate phase0-part01" to begin.**
