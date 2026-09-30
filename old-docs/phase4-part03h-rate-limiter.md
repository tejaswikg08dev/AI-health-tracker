# Phase 4 — Part 03h: Rate Limiter (middleware/rate_limiter.py) ⭐

| Field | Value |
|-------|-------|
| **Part** | 03h |
| **File** | `backend/app/middleware/rate_limiter.py` |
| **Next** | [Part 04 Overview — Auth Module](./phase4-part04-auth-module-overview.md) |
| **Difficulty** | 🟠 Hard |
| **Time to Type** | ~15 minutes |
| **Lines** | ~90 lines |

---

## What is Rate Limiting? Read This First

Rate limiting controls **how many requests** a client can make in a time window.

**Without rate limiting:**
- Attacker sends 1 million login attempts per minute → brute forces passwords
- Script sends 1000 AI chat requests → your LLM bill is $500
- Bot floods your API → legitimate users can't access the app (DDoS)

**With rate limiting:**
- Login: 5 requests per minute per IP → brute force takes 100+ years
- AI chat: 2 requests per second → max $0.50/user/day
- General API: 30 requests per second → normal usage unaffected

### Algorithm: Fixed Window Counter

```
Time: 10:00:00 ─── 10:01:00 ─── 10:02:00
      │ window 1    │ window 2    │
      │ count: 0    │ count: 0    │
      │             │             │
Req 1 │ count: 1 ✅  │             │
Req 2 │ count: 2 ✅  │             │
...   │             │             │
Req 60│ count: 60 ✅ │             │
Req 61│ count: 61 ❌ │             │ ← BLOCKED (429)
      │             │             │
      │ window ends │ count resets│
      │             │ count: 0    │
Req 62│             │ count: 1 ✅  │ ← allowed again
```

### Our 3 Rate Limit Zones

| Zone | Path | Limit | Why |
|------|------|-------|-----|
| General API | `/api/v1/` | 60 req/min | Normal usage |
| AI endpoints | `/api/v1/ai/` | 10 req/min | LLM calls are expensive |
| Login | `/api/v1/auth/login` | 5 req/min | Prevent brute force |

---

## Source Code

> 📁 **File:** `backend/app/middleware/rate_limiter.py`
> Type the full code from the source file

**Key Redis commands:**
```python
# 1. Build key: "rl:{ip}:{path}:{window_number}"
key = f"rl:{client_ip}:{path}:{window_start}"

# 2. Increment counter (atomic — safe for concurrent requests)
current_count = await redis.incr(key)

# 3. Set expiry on first request (auto-cleanup)
if current_count == 1:
    await redis.expire(key, window_seconds)

# 4. Check limit
if current_count > limit:
    return HTTP 429 "Too Many Requests"
```

**Fail-open design:** If Redis is down, requests pass through:
```python
except Exception:
    # Redis is down — DON'T block requests
    # Rate limiting is nice-to-have, not a hard gate
    return await call_next(request)
```

---

## 🎤 Interview Q&A

### Q: "How does your rate limiter work?"

> "Fixed window counter with Redis. For each request, I build a key combining the client IP, endpoint path, and current time window (time divided by window_seconds). Redis INCR atomically increments the counter. If it's the first request in the window, I set EXPIRE so the key auto-deletes. If the count exceeds the limit, I return HTTP 429 with Retry-After header. I have three zones: 60/min for general API, 10/min for AI (expensive LLM calls), and 5/min for login (brute force prevention). If Redis is down, I fail open — requests pass through. Rate limiting shouldn't be a single point of failure."

### Q: "What's the difference between fixed window and sliding window?"

> "Fixed window resets at exact boundaries (10:00, 10:01). A client could send 60 requests at 10:00:59 and 60 more at 10:01:00 — 120 requests in 2 seconds, defeating the limit. Sliding window counts requests in the last 60 seconds from NOW — no boundary gaming. I use fixed window for simplicity and performance (one INCR vs sorted set operations). For my scale (1000 users), the boundary edge case is acceptable. At higher scale, I'd switch to sliding window using Redis sorted sets."

### Q: "Why rate limit at both Nginx and application level?"

> "Defense in depth. Nginx rate limiting (configured in default.conf) uses the `limit_req` directive — it runs BEFORE the request reaches FastAPI, protecting against floods that would overwhelm the application. Application-level rate limiting (this middleware) uses Redis with user-aware rules — different limits per endpoint type. Nginx protects the server. The application protects the resources. Even if one layer fails, the other still works."

---

## ✅ Release 1.2 + 1.3 Complete!

All shared utilities and middleware are typed. These can't be tested independently yet — they need `main.py` (Part 04k) to wire everything together.

Move to [Part 04 — Auth Module](./phase4-part04-auth-module-overview.md) 🚀

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03g](./phase4-part03g-logging-middleware.md) | | [Part 04 Overview — Auth Module](./phase4-part04-auth-module-overview.md) |
