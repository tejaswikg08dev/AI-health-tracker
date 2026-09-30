# 🏥 AI-Powered Personal Health & Habit Tracker

A full-stack health tracking application with AI-powered insights, built as a learning project covering **Python, FastAPI, React, TypeScript, PostgreSQL, Redis, Docker, AI/LLM, RAG, Agents, and AWS**.

## Architecture

```
Frontend (React + TypeScript)
        │
    Nginx (Reverse Proxy)
        │
Backend (FastAPI — Modular Monolith)
    ├── Auth Module        (JWT, bcrypt)
    ├── Habits Module      (CRUD, soft delete)
    ├── Logs Module        (daily check-ins, bulk)
    ├── Analytics Module   (streaks, SQL window functions, Redis cache)
    ├── AI Module
    │   ├── LLM Layer      (Ollama / Groq / OpenAI — Strategy pattern)
    │   ├── RAG Pipeline   (PDF → chunks → pgvector → retrieval)
    │   ├── ReAct Agent    (5 tools, short + long term memory)
    │   └── Agentic Workflow (3-step weekly report pipeline)
    ├── Notifications      (email via Console / Resend / SES)
    └── Export             (CSV, S3/MinIO storage)
        │
    PostgreSQL + pgvector │ Redis │ MinIO (S3) │ Ollama (LLM)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery |
| **Frontend** | React 18, TypeScript, Vite, TanStack Query, Zustand, Recharts, Tailwind CSS |
| **Database** | PostgreSQL 16 + pgvector (vector search) |
| **Cache** | Redis 7 (caching, rate limiting, token blacklist, Celery broker) |
| **AI** | Ollama (free local), Groq (free cloud), OpenAI (production) |
| **Storage** | MinIO (local S3) / AWS S3 |
| **Proxy** | Nginx (reverse proxy, rate limiting, SSE support) |
| **CI/CD** | GitHub Actions (lint → test → build) |
| **Containers** | Docker + Docker Compose |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. Clone and configure
```bash
git clone https://github.com/your-username/health-tracker.git
cd health-tracker
cp .env.example .env
```

### 2. Start databases
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up postgres redis -d
```

### 3. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head        # Run database migrations
python -m scripts.seed_data # Seed demo data
uvicorn app.main:app --reload
```

### 4. Frontend setup
```bash
cd frontend
npm install
npm run dev
```

### 5. Access the app
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Login**: shreya@example.com / DemoPass123

## API Endpoints (38 total)

| Module | Endpoints | Methods |
|--------|-----------|---------|
| **Auth** | `/api/v1/auth/*` | signup, login, refresh, logout, profile |
| **Habits** | `/api/v1/habits/*` | CRUD, reorder |
| **Logs** | `/api/v1/logs/*` | create, bulk, query, update, delete |
| **Analytics** | `/api/v1/analytics/*` | dashboard, streaks, weekly, monthly, completion, correlations |
| **AI** | `/api/v1/ai/*` | chat, stream, history, documents, insights, weekly report |
| **Notifications** | `/api/v1/notifications/*` | settings, test email |
| **Export** | `/api/v1/export/*` | CSV download, S3 upload |

## Project Structure

```
health-tracker/
├── backend/           # FastAPI (Python)
│   ├── app/
│   │   ├── modules/   # 7 modules (auth, habits, logs, analytics, ai, notifications, export)
│   │   ├── shared/    # Base classes, utilities
│   │   └── middleware/ # Logging, rate limiting, error handling
│   ├── tests/         # pytest (unit + integration)
│   └── alembic/       # Database migrations
├── frontend/          # React + TypeScript
│   └── src/
│       ├── pages/     # 8 pages
│       ├── components/# Habits, logs, charts, AI chat
│       ├── hooks/     # TanStack Query hooks
│       ├── services/  # Axios API layer
│       └── store/     # Zustand auth state
├── nginx/             # Reverse proxy config
├── scripts/           # Seed data
├── docker-compose.yml # All services
└── .github/workflows/ # CI/CD pipeline
```

## AI Features

| Feature | What It Does |
|---------|-------------|
| **LLM Chat** | Conversational health coaching (Ollama/Groq/OpenAI) |
| **RAG** | Upload PDFs → chunk → embed → pgvector search → cited answers |
| **ReAct Agent** | 5 tools: query data, analytics, search docs, correlate, plan |
| **Agent Memory** | Short-term (conversation) + long-term (persistent insights) |
| **Agentic Workflow** | Weekly report: DataCollector → Analyzer → ReportWriter |
| **Streaming** | SSE word-by-word response in chat UI |

## Testing

```bash
# Unit tests (no database needed)
cd backend && python -m pytest tests/unit -v

# Integration tests (needs PostgreSQL + Redis)
docker-compose -f docker-compose.test.yml up -d
cd backend && python -m pytest tests/integration -v
docker-compose -f docker-compose.test.yml down
```

## Design Patterns Used

| Pattern | Where |
|---------|-------|
| Strategy | LLM providers, Email providers, Storage providers |
| Factory | `get_llm_client()`, `get_email_provider()` |
| Repository | Data access layer in every module |
| Service Layer | Business logic separated from HTTP |
| Cache-Aside | Analytics with Redis TTL caching |
| Abstract Base Class | `BaseLLMClient`, `BaseTool`, `BaseWorkflow` |
| ReAct Agent | Think → Act → Observe loop |
| Pipeline | Agentic weekly report workflow |
| Modular Monolith | 7 modules with clear boundaries |

## License

MIT — built for learning purposes.
