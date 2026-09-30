# 🛠️ Phase 0 — Part 03: Tech Stack Explained

> **"Choose boring technology for the foundation, interesting technology for the differentiator."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 0 — Overview & Setup |
| **Part** | 03 of 05 |
| **Previous** | [Part 02 — Architecture Overview](./phase0-part02-architecture-overview.md) |
| **Next** | [Part 04 — Environment Setup](./phase0-part04-environment-setup.md) |
| **Time to Read** | ~30 minutes |

---

## Why This Matters

Every technology in this project was chosen for a specific reason. In interviews, you'll be asked "Why FastAPI and not Django?" or "Why Redis and not Memcached?" This document gives you the answer for every choice.

---

## 🐍 Python 3.11

### What is Python?
A programming language designed for readability. Python reads almost like English:
```python
if user.is_active and password_matches:
    return create_token(user.id)
```

### Why Python for this project?
- **AI ecosystem:** 90% of AI/ML libraries are Python-first (LangChain, transformers, etc.)
- **FastAPI:** one of the fastest Python web frameworks (async)
- **Readability:** easier to learn and maintain than Java/Go for a first project

### Why 3.11?
- Type hints with `X | None` syntax (cleaner than `Optional[X]`)
- Faster than 3.10 (10-60% speed improvement)
- `match` statement, `ExceptionGroup`, better error messages

### Interview Q: "Why Python and not Node.js or Go?"
> "Python because of the AI ecosystem. 90% of LLM libraries, embedding tools, and vector database clients are Python-first. FastAPI gives me async performance comparable to Node.js, while Python's type hints give me the safety benefits of TypeScript. Go would be faster but has virtually no AI ecosystem."

---

## ⚡ FastAPI

### What is FastAPI?
A modern Python web framework for building APIs. "Fast" refers to both:
1. **Fast to run** — built on ASGI (async), handles thousands of concurrent requests
2. **Fast to code** — auto-generates API docs, validates requests automatically

### What is ASGI?
ASGI = Asynchronous Server Gateway Interface. It means FastAPI can handle many requests at once without blocking. While waiting for the database, it handles other requests.

**Analogy:** A restaurant waiter (WSGI/Django) takes one order, goes to the kitchen, waits for the food, brings it back, THEN takes the next order. A FastAPI waiter takes order 1, sends it to kitchen, takes order 2, sends it to kitchen, serves whichever is ready first.

### Why FastAPI and not Django/Flask?
| Feature | FastAPI | Django | Flask |
|---------|---------|--------|-------|
| Async | ✅ Native | ⚠️ Added later (3.1+) | ❌ No |
| Auto API docs | ✅ Swagger + ReDoc | ❌ Need django-rest-framework | ❌ Need flask-restful |
| Type validation | ✅ Pydantic built-in | ❌ Need serializers | ❌ Need marshmallow |
| Speed | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Learning curve | Medium | High (ORM, admin, templates) | Low but manual everything |

### Interview Q: "Why FastAPI over Django REST Framework?"
> "Three reasons. First, native async — my app calls external LLM APIs that take 2-10 seconds. With Django, that blocks the thread. With FastAPI, other requests are handled while waiting. Second, Pydantic validation is built into FastAPI — every request body is automatically validated against a typed schema, with auto-generated Swagger docs. Third, dependency injection via Depends() gives me clean testability — I can swap the real database for a test database by overriding one dependency."

---

## 🐘 PostgreSQL 16 + pgvector

### What is PostgreSQL?
A relational database — stores data in tables with rows and columns, linked by relationships (foreign keys). The most popular open-source database.

### What is pgvector?
An EXTENSION for PostgreSQL that adds a `vector` data type and similarity search operators. Instead of running a separate vector database (Pinecone, $70/month), we add vector search to our existing PostgreSQL ($0).

### Why PostgreSQL and not MySQL/MongoDB?
| Feature | PostgreSQL | MySQL | MongoDB |
|---------|-----------|-------|---------|
| JSON support | ✅ JSONB (fast) | ⚠️ Basic | ✅ Native |
| Window functions | ✅ Full | ⚠️ Limited | ❌ No |
| Vector search | ✅ pgvector | ❌ No | ✅ Atlas Vector Search |
| ACID transactions | ✅ Full | ✅ Full | ⚠️ Limited |
| Row-level security | ✅ | ❌ | ❌ |

### Interview Q: "Why PostgreSQL with pgvector instead of a separate vector database?"
> "Simplicity and cost. One database to manage, backup, and scale instead of two. pgvector handles up to ~1 million vectors with IVFFlat indexing, which is more than enough for a personal health tracker's document chunks. The vectors are stored in the same transaction as the document metadata — if the document insert fails, the vectors aren't orphaned. For 10 million+ vectors, I'd consider Pinecone, but that's a scaling problem I don't have yet."

---

## 🔴 Redis 7

### What is Redis?
An in-memory data store. Everything is stored in RAM, not disk. This means reads/writes take < 1 millisecond (100x faster than PostgreSQL).

### Why is it so fast?
PostgreSQL reads from disk → ~1-10ms. Redis reads from RAM → ~0.1ms. Like checking your pocket (RAM) vs going to the filing cabinet in another room (disk).

### 4 Use Cases in Our App

| Use Case | How | Why Redis (not PostgreSQL) |
|----------|-----|--------------------------|
| **Analytics cache** | `SET analytics:user:dashboard "{json}" EX 300` | Dashboard loads in 1ms instead of 200ms |
| **Rate limiting** | `INCR rl:ip:endpoint:window` | Checked on EVERY request — must be < 1ms |
| **JWT blacklist** | `SETEX token_blacklist:abc 1800 "blacklisted"` | Checked on EVERY request, auto-expires |
| **Celery broker** | Message queue for background tasks | Built-in support, no extra infrastructure |

### Interview Q: "Why Redis for caching and not just a Python dict?"
> "Three reasons. First, a Python dict lives in one process — if I have 4 FastAPI workers, each has its own cache. Redis is shared across all workers. Second, Redis has TTL (Time-To-Live) — cache entries automatically expire without cleanup code. Third, Redis persists across server restarts. If the FastAPI process crashes, the cache survives."

---

## 🤖 Ollama / Groq / OpenAI (LLM Providers)

### What is an LLM?
Large Language Model — a neural network that generates text. You give it a prompt ("How's my sleep?"), it generates a response ("Based on your data, you averaged 6.2 hours...").

### Why 3 Providers?

| Provider | Cost | Speed | Quality | When to Use |
|----------|------|-------|---------|-------------|
| **Ollama** | $0 | Slow (CPU) | Good | Local development |
| **Groq** | $0 | Very fast | Good | Deployed staging |
| **OpenAI** | $$$ | Medium | Best | Production (company pays) |

### Strategy Pattern
All three implement the SAME interface (`BaseLLMClient`). The `get_llm_client()` factory reads `LLM_PROVIDER=ollama` from the environment and returns the right one. The rest of the app doesn't know which provider is being used.

### Interview Q: "How do you handle different LLM providers?"
> "Strategy pattern. I defined an abstract `BaseLLMClient` with three methods: `chat()`, `stream_chat()`, and `embed()`. Three implementations: `OllamaClient` for free local dev, `GroqClient` for free cloud staging, `OpenAIClient` for paid production. A factory function reads `LLM_PROVIDER` from the environment and returns the right client. Swapping providers is a config change — zero code changes. The entire AI module — agents, RAG, workflows — calls the abstract interface, not a specific provider."

---

## 🐳 Docker + Docker Compose

### What is Docker?
Docker packages your application with ALL its dependencies into a "container" — a lightweight, isolated environment. "Works on my machine" becomes "works on EVERY machine."

### What is Docker Compose?
A tool that runs MULTIPLE Docker containers together. Our `docker-compose.yml` starts 7 services with ONE command:

```bash
docker-compose up
# Starts: PostgreSQL, Redis, MinIO, Ollama, Backend, Celery, Nginx
```

### Interview Q: "Why Docker?"
> "Reproducibility and consistency. Without Docker, a new developer needs to install Python 3.11, PostgreSQL 16, Redis 7, and configure each one. With Docker, `docker-compose up` starts everything with the exact versions I tested against. It also matches production — if it works in my Docker container, it works in the ECS Fargate container on AWS."

---

## 🌐 Nginx

### What is Nginx?
A web server that sits in FRONT of your application. It handles things the application shouldn't worry about: SSL certificates, rate limiting, static file serving, load balancing.

### How Does It Work?
```
Browser → Nginx (port 80) → FastAPI (port 8000)
                           → React build (static files)
```

Nginx is event-driven and non-blocking — one worker process handles THOUSANDS of connections simultaneously using epoll (Linux kernel feature).

### Interview Q: "How does Nginx work internally?"
> "Event-driven, non-blocking I/O. A master process spawns worker processes. Each worker uses epoll to monitor thousands of socket file descriptors simultaneously. When data arrives on any connection, the worker processes it and moves to the next ready connection — no thread-per-connection overhead like Apache. This is why Nginx handles 10,000+ concurrent connections with minimal RAM."

---

## ⚛️ React 18 + TypeScript

### What is React?
A JavaScript library for building user interfaces. You define components (reusable UI pieces), and React efficiently updates the browser when data changes.

### What is TypeScript?
JavaScript with types. Without types, you discover bugs at runtime (in production). With TypeScript, the IDE catches them while you type.

```typescript
// JavaScript — no error until user sees broken page
function getUser(id) { ... }
getUser("not-a-uuid")  // Breaks at runtime

// TypeScript — error before you even save the file
function getUser(id: string): Promise<User> { ... }
```

### Interview Q: "Why React + TypeScript instead of plain React?"
> "TypeScript catches bugs at compile time that JavaScript catches at runtime — or worse, in production. For a project with 7 API services, 24 hooks, and 50+ files, type safety prevents entire categories of bugs: wrong property names, missing fields, incorrect function arguments. The TypeScript interfaces mirror my backend Pydantic schemas, so if the API changes, TypeScript immediately shows every frontend file that needs updating."

---

## 📊 Summary Table

| Technology | Category | Why This One |
|-----------|----------|-------------|
| Python 3.11 | Language | AI ecosystem + FastAPI |
| FastAPI | Web framework | Async + Pydantic + auto docs |
| PostgreSQL + pgvector | Database | SQL + vector search in ONE DB |
| Redis 7 | Cache/broker | Sub-ms reads, 4 use cases |
| Ollama | LLM (dev) | Free, local, no API key |
| Groq | LLM (staging) | Free, fast, cloud |
| Docker Compose | Infrastructure | One command starts everything |
| Nginx | Reverse proxy | Rate limiting, SSE, static files |
| React 18 + TypeScript | Frontend | Type safety, Recharts, huge ecosystem |
| TanStack Query | Data fetching | Auto cache, refetch, mutations |
| Zustand | State management | 1KB, zero boilerplate |
| Tailwind CSS | Styling | Utility-first, no CSS files |
| GitHub Actions | CI/CD | Free, service containers |
| AWS Lambda | Serverless | 6 functions, free tier |

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 02 — Architecture](./phase0-part02-architecture-overview.md) | | [Part 04 — Environment Setup](./phase0-part04-environment-setup.md) |
