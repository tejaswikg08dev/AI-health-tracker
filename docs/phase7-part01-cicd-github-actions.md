# 🔄 Phase 7 Part 01: CI/CD — GitHub Actions Pipeline

> **"One workflow file, 5 jobs, 3 stages: lint (ruff + mypy + tsc in parallel), test (pytest with real PostgreSQL + Redis service containers), build (Docker images on main push only). Triggered on push to main/develop and PRs. Cost: $0."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 7 — Continuous Integration / Continuous Deployment |
| **Previous** | [Phase 6: Docker Deep Dive](./phase6-part01-docker-deep-dive.md) |
| **Next** | [Phase 8 Part 01: Local Deployment](./phase8-part01-deployment-local.md) |
| **Files in This Doc** | 1 file (.github/workflows/ci.yml) |
| **Time to Type** | ~25 minutes |
| **Difficulty** | Medium (YAML syntax, service containers, job dependencies) |

---

## 1. Pipeline Overview

```
                      Push to main/develop
                      or PR to main
                            │
               ┌────────────┼────────────┐
               ▼                         ▼
        lint-backend              lint-frontend
        (ruff + mypy)            (tsc --noEmit)
               │                         │
               ▼                         ▼
        test-backend              test-frontend
        (pytest + DB)             (npm run build)
               │                         │
               └────────────┬────────────┘
                            ▼
                     build-docker
                (main push only — not PRs)
```

**Three stages:**
1. **Lint** — catch style/type errors fast (~30 seconds)
2. **Test** — run full test suite with real databases (~2 minutes)
3. **Build** — build Docker images to confirm they compile (~1 minute)

---

## 2. `.github/workflows/ci.yml` — Full Source

### Type This Code:

```yaml
# ============================================================================
# CI/CD Pipeline — GitHub Actions
# ============================================================================
# TRIGGERS:
#   - Push to main or develop branches
#   - Pull requests to main
#
# COST: $0 — GitHub Actions is free for public repos (2,000 min/month)
# ============================================================================

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"

jobs:
  # ═══════════════════════════════════════════
  # Stage 1: Code Quality (runs in parallel)
  # ═══════════════════════════════════════════

  lint-backend:
    name: "Lint Backend (Python)"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install ruff mypy
          pip install -r backend/requirements.txt
        working-directory: .

      - name: Ruff lint
        run: ruff check app/
        working-directory: backend

      - name: Ruff format check
        run: ruff format --check app/
        working-directory: backend

      - name: MyPy type check
        run: mypy app/ --ignore-missing-imports
        working-directory: backend

  lint-frontend:
    name: "Lint Frontend (TypeScript)"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: TypeScript compile check
        run: npx tsc --noEmit
        working-directory: frontend

  # ═══════════════════════════════════════════
  # Stage 2: Tests (runs after lint passes)
  # ═══════════════════════════════════════════

  test-backend:
    name: "Test Backend (pytest)"
    needs: lint-backend
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: healthtracker_test
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6380:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: pip install -r requirements-dev.txt
        working-directory: backend

      - name: Run unit tests
        run: python -m pytest tests/unit -v --tb=short
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://testuser:testpass@localhost:5433/healthtracker_test
          DATABASE_URL_SYNC: postgresql://testuser:testpass@localhost:5433/healthtracker_test
          REDIS_URL: redis://localhost:6380/0
          SECRET_KEY: test-secret-key-for-ci
          LLM_PROVIDER: ollama
          EMAIL_PROVIDER: console

      - name: Run integration tests
        run: python -m pytest tests/integration -v --tb=short
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://testuser:testpass@localhost:5433/healthtracker_test
          DATABASE_URL_SYNC: postgresql://testuser:testpass@localhost:5433/healthtracker_test
          REDIS_URL: redis://localhost:6380/0
          SECRET_KEY: test-secret-key-for-ci
          LLM_PROVIDER: ollama
          EMAIL_PROVIDER: console

  test-frontend:
    name: "Build Frontend"
    needs: lint-frontend
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: Build
        run: npm run build
        working-directory: frontend

  # ═══════════════════════════════════════════
  # Stage 3: Build Docker Images (main only)
  # ═══════════════════════════════════════════

  build-docker:
    name: "Build Docker Images"
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build backend image
        run: docker build -t health-tracker-backend ./backend

      - name: Build frontend image
        run: docker build -t health-tracker-frontend ./frontend

      - name: Build successful
        run: echo "✅ All Docker images built successfully"
```

### Key Concepts

**`needs: lint-backend`** — Job dependency. `test-backend` only runs IF `lint-backend` passes. Saves CI minutes — no point running tests on code that doesn't lint.

**`services:` block** — GitHub Actions spins up real PostgreSQL and Redis containers alongside your test runner. Same images as `docker-compose.test.yml`. No mocking — real databases.

**`if: github.ref == 'refs/heads/main' && github.event_name == 'push'`** — The Docker build stage ONLY runs on pushes to main (not on PRs, not on develop). PRs get lint + test but not build — faster feedback.

**`npm ci` vs `npm install`** — `ci` installs EXACTLY what's in `package-lock.json` (deterministic). `install` might update packages. CI always uses `ci`.

**`cache: "npm"` + `cache-dependency-path`** — Caches `node_modules` between runs. If `package-lock.json` hasn't changed, npm doesn't reinstall 200+ packages. Saves ~45 seconds per run.

**`env:` block on steps** — Environment variables for that specific step. `SECRET_KEY: test-secret-key-for-ci` — a fake key for testing. Real secrets come from GitHub Secrets in production.

---

## 3. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **Pipeline stages** | Lint → Test → Build (fail fast) |
| 2 | **`needs:` dependencies** | Jobs run only if prerequisites pass |
| 3 | **Service containers** | Real PostgreSQL + Redis in CI |
| 4 | **`if:` conditional** | Build stage only on main push |
| 5 | **`npm ci`** | Deterministic installs from lockfile |
| 6 | **Dependency caching** | `cache: "npm"` — skip reinstall if unchanged |
| 7 | **`working-directory`** | Run commands in backend/ or frontend/ |
| 8 | **Parallel jobs** | lint-backend and lint-frontend run simultaneously |

---

## 4. Interview Questions

### Q1: "Walk me through your CI/CD pipeline."

**A:** "Three stages triggered on every push and PR. **Stage 1** (Lint) runs ruff, mypy, and tsc in parallel — catches style and type errors in ~30 seconds. **Stage 2** (Test) runs after lint passes. Backend tests use real PostgreSQL and Redis service containers — same images as production. Frontend does a full build to catch TypeScript/import errors. **Stage 3** (Build) only runs on pushes to main — builds Docker images to confirm they compile. In a production setup, this stage would push images to ECR and trigger an ECS deployment."

### Q2: "How would you add deployment to this pipeline?"

**A:** "I'd add a `deploy` job after `build-docker` that: (1) pushes images to AWS ECR using `aws-actions/configure-aws-credentials` + `docker push`, (2) updates the ECS task definition with the new image tag, (3) triggers an ECS service update. For Lambda, I'd add `sam build && sam deploy` with the SAM CLI GitHub Action. Secrets (AWS credentials) come from GitHub Secrets — never hardcoded in the workflow file."

---

## 5. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 6: Docker Deep Dive](./phase6-part01-docker-deep-dive.md) |
| ➡️ Next | [Phase 8 Part 01: Local Deployment](./phase8-part01-deployment-local.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**🎉 Phase 7 (CI/CD) is COMPLETE.**

*One workflow, 5 jobs, 3 stages. Lint and test on every push. Docker build only on main. Real databases in CI via service containers. $0 cost on GitHub's free tier. Next: deployment guides.*
