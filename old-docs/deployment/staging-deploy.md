# Staging Deployment — Free Tier Guide

Deploy the Health Tracker to the cloud for free using Render + Vercel + Supabase.

## Architecture

```
Frontend (Vercel — free)
    ↓ API calls
Backend (Render — free web service)
    ↓
Database: Supabase PostgreSQL (free, includes pgvector)
Cache: Upstash Redis (free, 10K commands/day)
AI: Groq API (free, 30 req/min)
```

## Step 1: Database — Supabase (Free)

1. Go to [supabase.com](https://supabase.com), create a project
2. In SQL Editor, enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Copy the connection string from Settings → Database → Connection String
4. It looks like: `postgresql://postgres:password@db.xxx.supabase.co:5432/postgres`

## Step 2: Redis — Upstash (Free)

1. Go to [upstash.com](https://upstash.com), create a Redis database
2. Copy the Redis URL (looks like: `rediss://default:xxx@xxx.upstash.io:6379`)

## Step 3: Backend — Render (Free)

1. Go to [render.com](https://render.com), connect your GitHub repo
2. Create a **Web Service**, select the `backend/` directory
3. Settings:
   - **Build Command:** `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command:** `gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
4. Environment variables:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres
   DATABASE_URL_SYNC=postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres
   REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
   SECRET_KEY=(generate a random string)
   LLM_PROVIDER=groq
   GROQ_API_KEY=(your free Groq key)
   EMAIL_PROVIDER=console
   CORS_ORIGINS=https://your-app.vercel.app
   APP_ENV=staging
   DEBUG=false
   ```

## Step 4: Frontend — Vercel (Free)

1. Go to [vercel.com](https://vercel.com), import the repo
2. Set the root directory to `frontend/`
3. Environment variable:
   ```
   VITE_API_URL=https://your-backend.onrender.com
   ```
4. Deploy — Vercel auto-builds on git push

## Step 5: Seed Data

```bash
# SSH into Render (or use Render Shell)
python -m scripts.seed_data
```

## Limitations of Free Tier

| Service | Limitation | Impact |
|---------|-----------|--------|
| Render | Sleeps after 15 min idle | First request takes ~30s to wake |
| Supabase | 500 MB storage | Plenty for a personal project |
| Upstash | 10K commands/day | Enough for ~100 page loads/day |
| Groq | 30 requests/min | Enough for casual AI chat use |
