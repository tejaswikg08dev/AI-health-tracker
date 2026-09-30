# 🏥 Phase 0 — Part 01: Project Overview

> **"Every great project starts with understanding WHAT you're building and WHY."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 0 — Overview & Setup |
| **Part** | 01 of 05 |
| **Previous** | — (this is the first document) |
| **Next** | [Part 02 — Architecture Overview](./phase0-part02-architecture-overview.md) |
| **Time to Read** | ~20 minutes |
| **You Will Type** | Nothing yet — this is understanding first |

---

## 🎯 What Are We Building?

We are building a **full-stack web application** that helps people track their daily health habits and get AI-powered insights about their health data.

### The One-Sentence Pitch

> "A personal health tracker where you log daily habits (water, sleep, exercise, mood), see streaks and charts, and chat with an AI health coach that can look at your actual data, search your uploaded health documents, and generate weekly health reports."

### If an Interviewer Asks "Tell Me About Your Project"

> "I built an AI-powered health habit tracker with a Python FastAPI backend and React TypeScript frontend. It has 7 backend modules handling authentication, habit tracking, analytics, AI chat, notifications, and data export. The AI module is the most interesting part — it uses a ReAct agent pattern with 5 custom tools that query real user data from the database, a RAG pipeline for searching uploaded health documents using pgvector, and an agentic workflow that generates personalized weekly health reports through a 3-step pipeline. The whole thing runs on Docker with PostgreSQL, Redis, Nginx, and Ollama for free local AI."

---

## 👤 Who Is This For?

A single user (you!) who wants to:
1. **Track** daily habits — water intake, sleep hours, exercise, mood rating
2. **See** their progress — streaks, weekly comparisons, monthly trends
3. **Understand** patterns — "Does my sleep affect my mood?" (correlations)
4. **Ask AI** questions — "Why am I tired this week?" (agent with tools)
5. **Upload documents** — blood reports, nutrition guides → AI can reference them
6. **Get reports** — AI-generated weekly health summary via email

---

## ✨ Features List

### Core Features (Modules 1-4)

| Feature | Module | What It Does |
|---------|--------|-------------|
| Sign up / Login | Auth | JWT authentication with access + refresh tokens |
| Create habits | Habits | 3 types: numeric (8 glasses), boolean (yes/no), scale (1-10) |
| Daily check-in | Logs | Log all habits at once with "Save All" button |
| Dashboard | Analytics | Today's progress, best streak, weekly completion |
| Streaks | Analytics | Consecutive days tracked (gaps-and-islands SQL algorithm) |
| Weekly comparison | Analytics | This week vs last week with % change |
| Monthly trends | Analytics | 30-day line chart per habit |
| Correlations | Analytics | "Sleep and mood have 0.72 correlation (strong positive)" |

### AI Features (Module 5)

| Feature | AI Subsystem | What It Does |
|---------|-------------|-------------|
| AI chat | LLM (Ollama/Groq) | Conversational health coaching |
| Data-aware answers | ReAct Agent | Agent queries YOUR database with 5 tools |
| Document Q&A | RAG Pipeline | Upload PDF → chunk → embed → search → cited answer |
| Streaming response | SSE | Response appears word-by-word like ChatGPT |
| Weekly report | Agentic Workflow | 3-step pipeline: collect → analyze → write |
| Long-term memory | Redis | Agent remembers "user is vegetarian" across sessions |

### Delivery Features (Modules 6-7)

| Feature | Module | What It Does |
|---------|--------|-------------|
| Email reminders | Notifications | "Time to log your habits!" daily at 8 AM |
| Streak celebrations | Notifications | "🔥 30-day streak!" milestone email |
| CSV export | Export | Download habit data as spreadsheet |
| Weekly report email | Notifications | AI-generated report sent every Sunday |

---

## 🏗️ Architecture at a Glance

```
     YOU (Browser)
      │
  React + TypeScript ────── 8 pages, charts, AI chat
      │
    Nginx ───────────────── Reverse proxy, rate limiting, SSE
      │
  FastAPI (Python) ──────── 7 modules, 38 API endpoints
   │     │      │
   │     │   Ollama ─────── Free local AI (Llama 3.1)
   │     │
   │  Redis ─────────────── Cache, rate limit, token blacklist
   │
PostgreSQL + pgvector ───── 8 tables, vector search for RAG
MinIO ───────────────────── S3-compatible file storage
```

---

## 📊 By the Numbers

| Metric | Count |
|--------|-------|
| Backend Python files | 100+ |
| Frontend TypeScript files | 50+ |
| API endpoints | 38 |
| Database tables | 8 |
| AI agent tools | 5 |
| LLM providers | 3 (Ollama free, Groq free, OpenAI paid) |
| Lambda functions | 6 |
| Docker services | 7 |
| React pages | 8 |
| Total cost to run | $0 (all free tier) |

---

## 🛠️ Tech Stack Quick Reference

| Layer | Technology | Why We Chose It |
|-------|-----------|----------------|
| **Backend** | Python 3.11 + FastAPI | Async, auto API docs, type safety, AI ecosystem |
| **Frontend** | React 18 + TypeScript | Type safety, huge ecosystem, Recharts for data viz |
| **Database** | PostgreSQL 16 + pgvector | SQL + vector search in ONE database |
| **Cache** | Redis 7 | Sub-millisecond reads, 4 different use cases |
| **AI (dev)** | Ollama (Llama 3.1) | Free, runs locally, no API key needed |
| **AI (cloud)** | Groq | Free tier (30 req/min), ultra-fast inference |
| **AI (prod)** | OpenAI GPT-4 | Best quality, company pays for it |
| **Proxy** | Nginx | Reverse proxy, rate limiting, SSE streaming |
| **Storage** | MinIO (local) / S3 (AWS) | Same boto3 API, free locally |
| **Containers** | Docker Compose | One command starts everything |
| **CI/CD** | GitHub Actions | Free for public repos |
| **Serverless** | AWS Lambda + SAM | 6 event-driven functions, free tier |

---

## 📐 Design Patterns You'll Learn

| Pattern | Where It's Used | Interview Value |
|---------|----------------|-----------------|
| **Strategy** | LLM providers (Ollama/Groq/OpenAI swap via config) | ⭐⭐⭐ |
| **Factory** | `get_llm_client()` returns the right provider | ⭐⭐⭐ |
| **Repository** | Every module: Router → Service → Repository layers | ⭐⭐⭐ |
| **Service Layer** | Business logic separated from HTTP concerns | ⭐⭐⭐ |
| **Cache-Aside** | Analytics cached in Redis with TTL | ⭐⭐ |
| **Abstract Base Class** | BaseLLMClient, BaseTool, BaseWorkflow | ⭐⭐ |
| **ReAct Agent** | Think → Act → Observe → Repeat loop | ⭐⭐⭐ |
| **Pipeline** | Agentic 3-step weekly report workflow | ⭐⭐ |
| **Modular Monolith** | 7 modules with clear service boundaries | ⭐⭐⭐ |
| **Dependency Injection** | FastAPI Depends() for DB sessions, Redis | ⭐⭐ |

---

## 📅 Sprint Timeline

| Sprint | Week | What You Build | Verification |
|--------|------|---------------|-------------|
| **Sprint 1** | Week 1 | Foundation + Auth | Signup, login, JWT tokens work |
| **Sprint 2** | Week 2 | Habits + Logs + Analytics | Track habits, see streaks and charts |
| **Sprint 3** | Week 3-4 | AI (LLM + RAG + Agents + Workflows) | Chat with AI, upload docs, weekly report |
| **Sprint 4** | Week 4 | Notifications + Export + Lambda | Emails, CSV download, serverless |
| **Sprint 5** | Week 5 | Frontend + Tests + Deploy | Full working app, tested, deployed |

---

## 🎤 Interview Q&A

### Q1: "What project have you worked on recently?"

> "I built an AI-powered personal health and habit tracker — a full-stack application with a Python FastAPI backend and React TypeScript frontend. Users track daily habits like water intake, sleep, and exercise. The app calculates streaks using SQL window functions, shows weekly comparisons and correlations, and has an AI health coach powered by a ReAct agent pattern. The AI can query the user's actual database, search uploaded health documents using RAG with pgvector, and generate personalized weekly reports through an agentic workflow pipeline. Everything runs on Docker with PostgreSQL, Redis, and free AI via Ollama."

### Q2: "Why did you choose this tech stack?"

> "FastAPI for its async support and automatic OpenAPI documentation — critical for a project with 38 endpoints. PostgreSQL with pgvector because I needed both relational data AND vector search for RAG, and using one database is simpler than managing PostgreSQL plus a separate Pinecone instance. Redis for four different use cases: caching analytics, rate limiting, JWT token blacklist, and Celery task broker. Ollama for development AI because it's free and runs locally — I used the Strategy pattern so I can swap to Groq or OpenAI with a single config change."

### Q3: "What's the most technically interesting part?"

> "The AI module. I built a ReAct agent from scratch — not using LangChain. The agent has a think-act-observe loop: when a user asks 'Why am I tired?', the agent decides to call the query_logs tool to check sleep data, then the correlate tool to check if sleep correlates with mood, then the search_documents tool to check their uploaded health reports. Each tool call queries the real PostgreSQL database. The agent makes up to 5 tool calls per question, then generates a response using the actual data. I also built a RAG pipeline: PDFs are chunked, embedded with nomic-embed-text, stored in pgvector, and retrieved using cosine similarity search."

### Q4: "What did you learn from this project?"

> "Three main things: First, the importance of architecture — the modular monolith pattern with Router → Service → Repository layers meant I could build and test each module independently. Second, that caching is not just 'add Redis' — the cache-aside pattern with proper invalidation on writes was crucial for analytics performance. Third, that AI agents are fundamentally different from simple LLM calls — the ReAct loop with tool calling gives much better answers because the AI reasons about what data it needs before answering."

---

## 📚 What's Next

This was the overview. Now let's understand HOW these pieces fit together.

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| — | | [Part 02 — Architecture](./phase0-part02-architecture-overview.md) |
