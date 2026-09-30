# System Design Interview Answers — From This Project

Prepared answers based on what you built. Read these before interviews.

---

## Q1: "Design a habit tracking application"

**Your answer:**

"I built this exact system. Here's the architecture:

**Modular monolith** with 7 modules: Auth, Habits, Logs, Analytics, AI, Notifications, Export. Each module follows Router → Service → Repository layers. I chose a modular monolith over microservices because it's a single-team project with one database — microservices would add operational overhead without benefit.

**Database:** PostgreSQL for relational data (users, habits, logs) with pgvector extension for AI embeddings. One database handles both OLTP and vector search.

**Caching:** Redis for analytics cache (cache-aside pattern with 5-30 min TTL), rate limiting (sliding window), JWT token blacklist, and Celery task broker.

**Key design:** Daily logs have a UNIQUE constraint on (user_id, habit_id, log_date) — one entry per habit per day. Streaks are calculated using the gaps-and-islands SQL pattern with window functions. Analytics are cached in Redis and invalidated when logs change.

**AI:** Three-provider LLM abstraction (Strategy pattern) — Ollama for dev, Groq for staging, OpenAI for production. RAG pipeline uses pgvector for semantic document search. ReAct agent with 5 tools for data-aware conversations."

---

## Q2: "How does your authentication work?"

**Your answer:**

"JWT-based authentication with access + refresh token pattern.

**Access token:** Short-lived (30 min), sent with every API request in the Authorization header. Contains user_id, token type, and expiry. If stolen, damage is limited to 30 minutes.

**Refresh token:** Long-lived (7 days), sent only to /auth/refresh. When the access token expires, the frontend silently calls refresh to get a new one — the user never notices.

**Password storage:** bcrypt with cost factor 12 (~100ms per hash). Never store plain text. Same error message for wrong email and wrong password — prevents email enumeration.

**Token blacklist:** On logout, the token is added to a Redis set with TTL matching the token's remaining lifetime. Every request checks the blacklist. Redis because it's checked on every single request — must be < 1ms.

**Security note:** Login endpoint has a stricter rate limit (5/min per IP vs 30/s for general API) to prevent brute force attacks."

---

## Q3: "How would you handle 10,000 concurrent users?"

**Your answer:**

"The current architecture handles this with minimal changes:

1. **FastAPI is async** — a single server handles thousands of concurrent connections via Python's event loop. No thread-per-request bottleneck.

2. **Connection pooling** — SQLAlchemy pool of 20 connections with 10 overflow. PostgreSQL handles ~100 concurrent connections comfortably.

3. **Redis caching** — Dashboard analytics are cached for 5 minutes. 10,000 users hitting the dashboard = 10,000 Redis GETs (< 1ms each), not 10,000 complex SQL queries.

4. **Horizontal scaling** — Deploy 2-10 FastAPI containers behind an ALB (AWS) or Nginx (Docker). Stateless JWT auth means any container can handle any request.

5. **Background offloading** — Expensive operations (email, reports, CSV export) go through SQS → Lambda. The API responds immediately: 'Your export is processing.'

6. **Database scaling** — Read replicas for analytics queries. Analytics module reads can be routed to a replica; writes (new logs) go to the primary.

For 100K+ users, I'd extract the AI module into a separate service (it's already a clean module boundary) and use AWS Bedrock for managed LLM scaling."

---

## Q4: "Why modular monolith instead of microservices?"

**Your answer:**

"Three reasons:

1. **Single team** — I'm the only developer. Microservices need: service discovery, distributed tracing, API gateways, eventual consistency handling, separate CI/CD per service. That's 3 months of infrastructure before writing any business logic.

2. **Shared database** — All modules read from the same PostgreSQL. In microservices, each service owns its database. Habits + Logs + Analytics all query `habit_logs` — splitting that into 3 databases means distributed joins or data duplication.

3. **Same process, clear boundaries** — Each module has its own models, services, and repository. Modules communicate through service interfaces, never direct SQL. If scale demands it, I can extract any module into a microservice — just replace the service method call with an HTTP call. Zero business logic changes.

Companies like Shopify (10M+ merchants) and GitHub run on modular monoliths. It's not a compromise — it's a deliberate architecture choice."

---

## Q5: "Explain your caching strategy"

**Your answer:**

"Cache-aside pattern with Redis.

**What's cached:** Analytics results — dashboard summary (5 min TTL), streaks (30 min), weekly comparison (30 min), monthly trend (1 hour), correlations (1 hour). These are expensive SQL queries with window functions — 50-200ms each.

**How it works:**
1. Request comes in → check Redis
2. Cache HIT → return immediately (< 1ms)
3. Cache MISS → query PostgreSQL → compute result → store in Redis with TTL → return

**Invalidation:** When a user creates, updates, or deletes a log, the LogService calls `_invalidate_cache(user_id)` which deletes all `analytics:{user_id}:*` keys from Redis using SCAN.

**Why SCAN (not KEYS):** KEYS blocks Redis for all clients. SCAN iterates non-blockingly — safe in production.

**Trade-off:** First request after a cache invalidation is slow (100ms). All subsequent requests for the next 5-30 minutes are fast (1ms). For a personal health tracker with 1-5 logs per day, this is ideal."

---

## Q6: "How does your AI agent work?"

**Your answer:**

"ReAct pattern — Reason + Act loop.

The agent receives a user question and has access to 5 tools: query habit data, get analytics, search documents (RAG), calculate correlations, and create improvement plans.

**The loop:**
1. Send the question + tool descriptions to the LLM
2. LLM decides: 'I need sleep data' → returns a tool call
3. Agent executes the tool → gets real data from the database
4. Feed the tool result back to the LLM
5. LLM decides: 'I need one more thing' or 'I have enough to answer'
6. Repeat until final text response (max 5 iterations)

**Why max iterations:** Prevents infinite loops if the LLM keeps requesting tools. After 5 rounds, we ask for the best answer with gathered data.

**Memory:** Short-term (conversation buffer, last 20 messages, in-memory) lets the agent handle follow-up questions. Long-term (Redis hash, persists across sessions) stores facts like 'user is vegetarian' so the agent remembers next time.

**Provider abstraction:** The agent works with any LLM — Ollama locally, Groq free cloud, OpenAI production. The Strategy pattern means swapping providers is a config change, not a code change."

---

## Q7: "What is RAG and how did you implement it?"

**Your answer:**

"RAG = Retrieval-Augmented Generation. Instead of the LLM making up answers, we feed it relevant information from the user's documents.

**Ingestion pipeline:**
Upload PDF → extract text (PyPDF2, page-by-page) → chunk into ~500 token pieces with 50-token overlap (recursive splitter that prefers paragraph boundaries) → embed each chunk (nomic-embed-text, 768 dimensions) → store in PostgreSQL with pgvector extension.

**Retrieval pipeline:**
User asks 'What's my iron level?' → embed the question → cosine similarity search in pgvector → top 5 chunks above 0.3 threshold → filter by token budget (max 2000 tokens) → format with source citations → inject into the LLM prompt.

**Why pgvector (not Pinecone):** Free, same database as our app data, transactional (document + chunks in one commit), good enough for < 1M vectors. IVFFlat index gives ~95% recall with 10-100x speed improvement.

**Why chunking matters:** LLMs have token limits. A 50-page PDF is ~25K tokens — won't fit. 500-token chunks mean we retrieve just the relevant paragraph, not the whole document. Overlap prevents losing context at chunk boundaries."

---

## Q8: "How does Nginx work in your setup?"

**Your answer:**

"Nginx sits in front of everything as a reverse proxy.

**Architecture:** Browser → Nginx (:80) → FastAPI (:8000). Nginx also serves static React files directly.

**How Nginx handles 10K connections:** Event-driven, non-blocking I/O. One master process spawns worker processes. Each worker uses epoll (Linux) to handle thousands of connections simultaneously — no thread-per-connection like Apache. This is why Nginx uses ~50MB RAM for 10K connections.

**What Nginx does in my project:**
1. **Reverse proxy** — routes `/api/*` to FastAPI, `/` to React static files
2. **Rate limiting** — 3 zones: API (30r/s), AI (2r/s), login (5r/min)
3. **Security headers** — X-Frame-Options, X-Content-Type-Options, XSS protection
4. **Gzip compression** — 100KB JSON → ~15KB compressed
5. **SSE support** — `proxy_buffering off` for AI chat streaming
6. **Connection pooling** — `keepalive 32` to backend (reuse TCP connections)
7. **Custom error pages** — JSON 429/502/504 instead of HTML

**In production:** Nginx runs as a sidecar container in ECS Fargate alongside FastAPI."
