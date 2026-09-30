# 🚀 Phase 8 Part 02: Deployment — Staging (Free Tier)

> **"Deploy a staging environment for $0 using free-tier services: Railway or Render for the backend, Neon for PostgreSQL, Upstash for Redis, Groq for LLM. Enough to demo the app and run integration tests against a real cloud environment."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [Phase 8 Part 01: Local Deployment](./phase8-part01-deployment-local.md) |
| **Next** | [Phase 8 Part 03: AWS Production](./phase8-part03-deployment-aws-production.md) |

---

## 1. Free-Tier Service Map

| Service | Local (Docker) | Staging (Free) | Cost |
|---------|---------------|-----------------|------|
| **Backend** | Docker container | Railway / Render | $0 (500 hrs/month) |
| **PostgreSQL** | pgvector container | Neon.tech | $0 (0.5 GB storage) |
| **Redis** | Redis container | Upstash | $0 (10K commands/day) |
| **LLM** | Ollama (local) | Groq Cloud | $0 (14.4K req/day) |
| **S3 Storage** | MinIO container | Cloudflare R2 | $0 (10 GB) |
| **Email** | Console (logs) | Resend | $0 (100 emails/day) |
| **Frontend** | Vite dev server | Vercel / Netlify | $0 (100 GB bandwidth) |

**Total monthly cost: $0**

---

## 2. Architecture: Staging

```
Browser → Vercel (React SPA)
              │
              ├── /api/* → Railway (FastAPI backend)
              │                │
              │                ├── Neon (PostgreSQL + pgvector)
              │                ├── Upstash (Redis)
              │                ├── Groq (LLM API)
              │                ├── Cloudflare R2 (S3-compatible)
              │                └── Resend (Email)
              │
              └── Static assets served by Vercel CDN
```

---

## 3. Step-by-Step: Deploy Backend to Railway

### 3a. Create Neon PostgreSQL

1. Sign up at [neon.tech](https://neon.tech)
2. Create a project: "health-tracker-staging"
3. Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
4. Copy the connection string:
   ```
   postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/healthtracker?sslmode=require
   ```

### 3b. Create Upstash Redis

1. Sign up at [upstash.com](https://upstash.com)
2. Create a Redis database: "health-tracker-staging"
3. Copy the Redis URL:
   ```
   rediss://default:xxx@us1-xxx.upstash.io:6379
   ```

### 3c. Deploy Backend to Railway

1. Sign up at [railway.app](https://railway.app)
2. "New Project" → "Deploy from GitHub Repo"
3. Select your health-tracker repo
4. Set **Root Directory**: `backend`
5. Set **Build Command**: `pip install -r requirements.txt`
6. Set **Start Command**: `gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
7. Add environment variables:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/healthtracker?ssl=require
DATABASE_URL_SYNC=postgresql://user:pass@ep-xxx.neon.tech/healthtracker?ssl=require
REDIS_URL=rediss://default:xxx@us1-xxx.upstash.io:6379
SECRET_KEY=<generate-random-key>
LLM_PROVIDER=groq
GROQ_API_KEY=<your-groq-key>
EMAIL_PROVIDER=resend
RESEND_API_KEY=<your-resend-key>
APP_ENV=staging
DEBUG=false
CORS_ORIGINS=https://your-app.vercel.app
```

8. Run migrations: Railway console → `alembic upgrade head`

### 3d. Deploy Frontend to Vercel

1. Sign up at [vercel.com](https://vercel.com)
2. Import your GitHub repo
3. Set **Root Directory**: `frontend`
4. Set **Build Command**: `npm run build`
5. Set **Output Directory**: `dist`
6. Add environment variable:
   ```
   VITE_API_URL=https://your-backend.railway.app
   ```
7. Deploy — Vercel builds and serves the React SPA

---

## 4. Key Differences: Local vs Staging

| Aspect | Local | Staging |
|--------|-------|---------|
| Database | `localhost:5432` | Neon (cloud, SSL required) |
| Redis | `localhost:6379` | Upstash (`rediss://` = TLS) |
| LLM | Ollama (local, free, slow) | Groq (cloud, free, fast) |
| Storage | MinIO (local S3) | Cloudflare R2 (real S3-compatible) |
| Email | Console (prints to log) | Resend (sends real emails) |
| Frontend | Vite dev server + proxy | Vercel CDN + API URL env var |
| HTTPS | No (http://localhost) | Yes (automatic via Railway/Vercel) |

**Same code, different config.** The `.env` file controls which services are used. The Strategy pattern (LLM, email, storage) makes swapping providers a config change, not a code change.

---

## 5. Navigation

| ⬅️ Previous | [Phase 8 Part 01: Local Deployment](./phase8-part01-deployment-local.md) |
| ➡️ Next | [Phase 8 Part 03: AWS Production](./phase8-part03-deployment-aws-production.md) |

---

**End of Phase 8 Part 02: Staging Deployment (Free Tier)**
