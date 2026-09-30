# 🎬 Visual Documentation Plan — Health Tracker

> **Animated visual guides: architecture diagrams, setup walkthroughs, feature demos, testing flows, and AWS deployment — all as interactive HTML pages with CSS animations.**

---

## 📋 Why Visual Docs?

1. **Portfolio** — Recruiters spend 30 seconds on your GitHub. Animated visuals grab attention.
2. **Interviews** — "Let me show you how it works" is 10x more powerful than "Let me explain."
3. **Learning** — You (Shreya) understand the system better by seeing data flow animated.
4. **Demo** — No need to run the app live during interviews — the visual docs ARE the demo.

---

## 🛠️ Technology Choice

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **HTML + CSS animations** | Zero dependencies, works offline, GitHub Pages | Manual work | ✅ CHOSEN |
| PowerPoint/Google Slides | Easy to make | Static, not in repo | ❌ |
| Video recordings | Shows real app | Large files, can't update | ❌ |
| Mermaid diagrams | In markdown | No animations, limited styling | ❌ |
| D3.js | Powerful | Complex, overkill | ❌ |

**Approach:** Self-contained HTML files with embedded CSS animations. Open in any browser. Host on GitHub Pages. No npm, no build step.

---

## 📁 File Structure

```
health-tracker/
└── visual-docs/
    ├── index.html                          ← Landing page (links to all visual docs)
    ├── shared/
    │   └── styles.css                      ← Shared animations, colors, layout
    │
    ├── 01-architecture-overview.html       ← Full system architecture (animated)
    ├── 02-request-flow.html                ← HTTP request lifecycle (step-by-step)
    ├── 03-dev-setup.html                   ← Dev environment setup walkthrough
    ├── 04-feature-demo.html                ← All features demonstrated visually
    ├── 05-testing-flow.html                ← Test execution walkthrough
    ├── 06-docker-services.html             ← Container orchestration visual
    ├── 07-cicd-pipeline.html               ← GitHub Actions pipeline animation
    ├── 08-aws-deployment.html              ← AWS production architecture + deploy steps
    ├── 09-ai-deep-dive.html                ← AI module: LLM, RAG, Agent, Workflow animated
    └── 10-database-schema.html             ← 8 tables with relationships animated
```

---

## 📄 Document-by-Document Plan

---

### 01 — Architecture Overview (`01-architecture-overview.html`)

**What it shows:** The complete system — frontend, nginx, backend modules, databases, Lambda, CI/CD — with animated data flow arrows.

**Animations:**
1. **Load animation** — Components fade in one by one: Frontend → Nginx → Backend → DB → Lambda
2. **Click "Login Flow"** — Arrows animate: Browser → Nginx → Auth Router → Security → DB → JWT → Browser
3. **Click "AI Chat Flow"** — Arrows animate: Browser → AI Router → Agent → Tool → DB → LLM → Browser
4. **Click "Lambda Flow"** — Arrows animate: EventBridge → Lambda → DB → SES → Email
5. **Hover any component** — Tooltip shows: file count, tech used, key features

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  [Frontend]  →  [Nginx]  →  [Backend Modules]           │
│   React 18       Rate         ┌─────────────────┐       │
│   TypeScript     Limit        │ Auth  │ Habits  │       │
│   TanStack       Gzip         │ Logs  │ Analytics│      │
│   Zustand        SSE          │ AI    │ Notif   │       │
│                               │ Export│         │       │
│                               └───┬─────────┬──┘       │
│                                   │         │           │
│                              [PostgreSQL] [Redis]       │
│                              +pgvector    Cache         │
│                                                         │
│  [Lambda Functions]  ←  [SQS/EventBridge/S3]            │
│   6 serverless           Triggers                       │
└─────────────────────────────────────────────────────────┘
```

**CSS Techniques:** `@keyframes` for arrow flow, `transition` on hover, `animation-delay` for sequential fade-in, SVG path animations for data flow lines.

---

### 02 — Request Flow (`02-request-flow.html`)

**What it shows:** One HTTP request traced through ALL layers, step by step.

**Example: POST /api/v1/logs (create a habit log)**

**Animations (auto-play timeline with pause/play button):**

| Step | Layer | What Happens | Time |
|------|-------|-------------|------|
| 1 | Browser | User clicks "Save" on Check-In page | 0s |
| 2 | React | `useBulkCreateLogs.mutateAsync(data)` → axios POST | 0.5s |
| 3 | Axios | Request interceptor attaches JWT: `Authorization: Bearer eyJ...` | 1s |
| 4 | Nginx | Rate limit check (30r/s) → PASS → proxy to :8000 | 1.5s |
| 5 | FastAPI Middleware | LoggingMiddleware: generate request_id, start timer | 2s |
| 6 | FastAPI Middleware | RateLimiterMiddleware: Redis check → PASS | 2.5s |
| 7 | FastAPI Router | `log_router.bulk_create()` → Depends(get_current_user_id) | 3s |
| 8 | Auth Dependency | decode_token(JWT) → extract user_id | 3.5s |
| 9 | Service Layer | `LogService.bulk_create_logs()` → validate dates, types | 4s |
| 10 | Repository | `LogRepository.create()` × 6 → INSERT INTO habit_logs | 4.5s |
| 11 | Database | PostgreSQL: 6 rows inserted, commit | 5s |
| 12 | SQS | Send streak check messages (async, non-blocking) | 5.5s |
| 13 | Response | 201 Created → JSON array of 6 logs | 6s |
| 14 | TanStack Query | `invalidateQueries(LOGS_KEY)` + `invalidateQueries(ANALYTICS_KEY)` | 6.5s |
| 15 | UI Update | Check-in page shows green checkmarks ✅ | 7s |

**Visual:** Vertical timeline with each layer as a colored band. A glowing dot travels down through each layer. Code snippets appear beside each step.

---

### 03 — Dev Environment Setup (`03-dev-setup.html`)

**What it shows:** Complete setup from zero to running app, animated step by step.

**Sections:**

**A. Prerequisites (animated checklist)**
- Docker Desktop → animated install → green checkmark
- Git → animated install → green checkmark
- Node.js 20 → animated install → green checkmark

**B. Clone & Configure (terminal animation)**
```
$ git clone https://github.com/shreya/health-tracker.git
  Cloning into 'health-tracker'... ████████████ 100%
$ cd health-tracker
$ cp .env.example .env
  ✅ Environment configured
```

**C. Start Services (Docker animation)**
- `make dev` → animated container startup:
  - PostgreSQL container: spinning up → health check → ✅ ready
  - Redis container: spinning up → health check → ✅ ready
  - MinIO container: spinning up → ✅ ready
  - Ollama container: spinning up → ✅ ready
  - Backend container: building → installing deps → ✅ running on :8000

**D. Migrations (database animation)**
- `make migrate` → animated table creation:
  - Migration 001: users table appears
  - Migration 002: habits table appears with FK arrow to users
  - Migration 003: habit_logs table appears with FK arrows
  - Migration 004: AI tables appear (documents, chunks with vector icon)
  - Migration 005: notification_settings appears

**E. Pull LLM Models (download animation)**
- `make setup-ollama` → animated download bar:
  - llama3.1:8b ████████████ 4.7 GB ✅
  - nomic-embed-text ████████ 274 MB ✅

**F. Seed Data (data animation)**
- `make seed` → animated data insertion:
  - User: Shreya → ✅
  - 6 Habits appear (💧😴🏃😊📖🧘) → ✅
  - 90 days of logs fill in as a heatmap → ✅

**G. Verify (browser animation)**
- http://localhost:8000/docs → Swagger UI screenshot
- http://localhost:3000 → Login page → Dashboard with data

---

### 04 — Feature Demo (`04-feature-demo.html`)

**What it shows:** Every user-facing feature with animated mockup screens.

**Sections (click tabs to switch):**

| Tab | Feature | Animation |
|-----|---------|-----------|
| 🔑 Auth | Signup → Login → JWT flow | Form fills → token appears → redirect |
| 📋 Habits | Create Water Intake habit | Form: type selector, color picker, icon picker → card appears |
| ✅ Check-In | Log all 6 habits | Numeric input, boolean toggle, scale slider → Save All → green checks |
| 📊 Dashboard | 4 summary cards + streaks | Numbers count up, streak flames animate |
| 📈 Analytics | 4 tabs with charts | Bar chart draws, line chart traces, pie chart fills |
| 🤖 AI Chat | Ask "How's my sleep?" | User bubble → thinking dots → agent calls tool → response streams in |
| 📁 Export | Download CSV | Click → progress bar → file downloads |
| ⚙️ Settings | Update profile + test email | Form update → success toast → email preview |

**Each tab shows:** Animated mockup screen (CSS only, no real app needed) + the API call happening underneath + the database query running.

---

### 05 — Testing Flow (`05-testing-flow.html`)

**What it shows:** Test execution animated — what happens when you run `make test`.

**Animations:**

**A. Unit Tests (no DB)**
```
pytest tests/unit -v
  ✅ test_hash_password_returns_hash       0.01s
  ✅ test_verify_correct_password          0.01s
  ✅ test_verify_wrong_password            0.01s
  ... (38 tests tick by)
  ━━━━━━━━━━━ 38 passed in 1.8s ━━━━━━━━━━━
```
Each test name appears and gets a green checkmark with a timing.

**B. Integration Tests (with DB)**
- Docker: postgres-test + redis-test containers spin up (animated)
- Tests run: signup → login → create habit → log → verify (animated API calls)
- Docker: containers stop (animated teardown)
```
  ━━━━━━━━━━━ 24 passed in 8.2s ━━━━━━━━━━━
```

**C. Coverage Report (animated bar chart)**
- app/modules/auth: 92% ████████████████████░░
- app/modules/habits: 88% ██████████████████░░░
- app/modules/logs: 85% █████████████████░░░░
- TOTAL: 78% █████████████████░░░░ (above 70% threshold ✅)

---

### 06 — Docker Services (`06-docker-services.html`)

**What it shows:** All 8 Docker containers, their connections, and startup sequence.

**Animation:** Containers appear one by one in dependency order:
1. PostgreSQL + Redis (no dependencies — start first)
2. MinIO + Ollama (no dependencies)
3. Backend (waits for PostgreSQL ✅ + Redis ✅)
4. Celery Worker + Beat (waits for PostgreSQL ✅ + Redis ✅)
5. Nginx (waits for Backend ✅)

**Visual:** Each container is a colored box with name, image, port, and health status. Arrows show connections (backend → postgres, backend → redis, nginx → backend). Health checks pulse green.

**Interactive:** Click any container to see its docker-compose config and environment variables.

---

### 07 — CI/CD Pipeline (`07-cicd-pipeline.html`)

**What it shows:** GitHub Actions pipeline animated from push to deploy.

**Animation (triggered by clicking "Push to main"):**

Stage 1 — Lint (parallel):
```
lint-backend:  ruff check ████ OK → ruff format ████ OK → mypy ████ OK   ✅ 32s
lint-frontend: npm ci ████ → tsc --noEmit ████ OK                        ✅ 28s
```

Stage 2 — Test (after lint):
```
test-backend:  🐘 PostgreSQL starting... ✅ → 🔴 Redis starting... ✅
               pytest unit ████████ 38 passed → pytest integration ████████ 24 passed   ✅ 2m 15s
test-frontend: npm ci ████ → npm run build ████ OK                                     ✅ 1m 30s
```

Stage 3 — Build (after test, main only):
```
build-docker:  docker build backend ████████ OK → docker build frontend ████████ OK    ✅ 1m 45s
```

**Final:** Big green checkmark: "Pipeline passed ✅ — 4m 30s total"

---

### 08 — AWS Deployment (`08-aws-deployment.html`)

**What it shows:** Production AWS architecture + step-by-step deployment animation.

**Section A: Architecture (animated diagram)**
- CloudFront → ALB → ECS Fargate (3 tasks auto-scaling)
- Private subnet: RDS PostgreSQL + ElastiCache Redis
- Lambda functions triggered by EventBridge/SQS/S3
- All connected with animated arrows showing data flow

**Section B: Deploy Steps (animated timeline)**

| Step | Command | What Happens (animated) |
|------|---------|------------------------|
| 1 | `docker build` | Dockerfile stages animate: builder → production |
| 2 | `docker push` → ECR | Image uploads to AWS (progress bar) |
| 3 | ECS Task Definition | JSON config appears, highlights key fields |
| 4 | ECS Service Update | Old tasks drain, new tasks start (rolling update) |
| 5 | ALB Health Check | Green dots appear on healthy targets |
| 6 | CloudFront | S3 bucket with React build, CDN edge locations light up on world map |
| 7 | `sam deploy` | Lambda functions deploy (6 cards flip to "deployed") |
| 8 | Route 53 | Domain name → CloudFront → ALB → ECS (animated DNS resolution) |

**Section C: Cost Dashboard (animated counters)**
- ECS: $30/month (counter ticks)
- RDS: $15/month
- ElastiCache: $12/month
- Lambda: $0 (free tier)
- Total: $~80/month

---

### 09 — AI Deep Dive (`09-ai-deep-dive.html`)

**What it shows:** The 4 AI sub-systems animated.

**Tab 1: LLM Strategy Pattern**
- 3 provider cards (Ollama/Groq/OpenAI) — click one to "select"
- Animated: config changes → factory returns different client → same chat() call works

**Tab 2: RAG Pipeline**
- PDF uploads → text extraction (pages peel apart)
- Text → chunks (text splits with overlap highlighted)
- Chunks → embeddings (numbers flow into vector space dot plot)
- Query → cosine similarity (query dot approaches nearest chunk dots)
- Top-5 chunks + LLM → answer with citations

**Tab 3: ReAct Agent**
- User asks "Why am I tired?"
- Think bubble: "I should check sleep data"
- Tool call: query_logs → data table appears
- Think bubble: "Low sleep. Check correlation"
- Tool call: correlate → correlation number appears
- Final answer streams in word by word

**Tab 4: Weekly Report Workflow**
- 3 pipeline stages animate sequentially:
  - DataCollector: database queries → structured summary
  - Analyzer: LLM call → patterns + insights
  - ReportWriter: LLM call → friendly markdown report
- Token counter ticks up at each LLM call

---

### 10 — Database Schema (`10-database-schema.html`)

**What it shows:** All 8 tables with columns, types, relationships, and sample data.

**Animation:**
1. Tables appear one by one (in migration order)
2. FK arrows draw between tables (users → habits → habit_logs)
3. Click any table to see sample data rows
4. Click a relationship arrow to see the JOIN query
5. Hover a column to see its type, constraints, and which Part of the docs covers it

**Tables:**
```
users (Part 04) ←──── habits (Part 05) ←──── habit_logs (Part 06)
   │                                              │
   ├──── notification_settings (Part 13)          │
   │                                              ↓
   ├──── documents (Part 09) ←── document_chunks  analytics queries (Part 07)
   │                              (pgvector)
   ├──── ai_chat_messages (Part 12)
   └──── ai_insights (Part 11/12)
```

---

## 🎨 Shared Design System (`shared/styles.css`)

| Element | Style |
|---------|-------|
| **Colors** | Brand blue (#3B82F6), green (#10B981), orange (#F59E0B), red (#EF4444) |
| **Font** | Inter (Google Fonts) or system sans-serif |
| **Animations** | Smooth 0.3s transitions, 60fps CSS transforms |
| **Layout** | Max-width 1200px, centered, responsive |
| **Dark mode** | `prefers-color-scheme: dark` media query |
| **Code blocks** | Syntax-highlighted with CSS (no JS library needed) |
| **Interactive** | CSS `:hover`, `:focus`, `:checked` for tab switching (no JS needed for tabs) |

---

## 📋 Implementation Order

| # | File | Priority | Estimated Time | Lines (HTML+CSS) |
|---|------|----------|----------------|-------------------|
| 1 | `shared/styles.css` | Foundation | 1 hour | ~300 |
| 2 | `index.html` | Landing page | 30 min | ~150 |
| 3 | `01-architecture-overview.html` | Highest (portfolio centerpiece) | 2 hours | ~600 |
| 4 | `04-feature-demo.html` | High (shows what app does) | 2 hours | ~800 |
| 5 | `03-dev-setup.html` | High (practical for anyone cloning) | 1.5 hours | ~500 |
| 6 | `02-request-flow.html` | Medium (deep technical) | 1.5 hours | ~500 |
| 7 | `09-ai-deep-dive.html` | Medium (impressive for AI roles) | 2 hours | ~700 |
| 8 | `08-aws-deployment.html` | Medium (impressive for DevOps) | 1.5 hours | ~600 |
| 9 | `06-docker-services.html` | Lower | 1 hour | ~400 |
| 10 | `07-cicd-pipeline.html` | Lower | 1 hour | ~400 |
| 11 | `05-testing-flow.html` | Lower | 1 hour | ~350 |
| 12 | `10-database-schema.html` | Lower | 1 hour | ~400 |
| **Total** | | | **~16 hours** | **~5,700 lines** |

---

## 🚀 Hosting

```bash
# Option 1: GitHub Pages (free)
# Push visual-docs/ to the repo, enable GitHub Pages on /visual-docs

# Option 2: Open locally
# Just double-click any .html file — they're self-contained

# Option 3: Vercel/Netlify
# Deploy the visual-docs/ folder as a static site
```

---

## ✅ Summary

| Metric | Value |
|--------|-------|
| Total visual docs | 10 HTML pages + 1 CSS + 1 index |
| Total lines | ~5,700 (HTML + CSS) |
| Dependencies | Zero (pure HTML + CSS) |
| JavaScript | Minimal (only for play/pause on timelines) |
| Works offline | Yes (self-contained) |
| Mobile responsive | Yes (CSS media queries) |
| Dark mode | Yes (CSS prefers-color-scheme) |
| Hosting | GitHub Pages (free) |

**These visual docs turn your project from "a GitHub repo with code" into "an interactive portfolio piece that impresses in seconds."**

---

*Ready to start? Say "continue" and I'll begin creating these files, starting with the shared CSS and architecture overview.*
