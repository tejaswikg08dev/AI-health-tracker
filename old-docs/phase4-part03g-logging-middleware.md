# Phase 4 — Part 03g: Request Logging Middleware

| Field | Value |
|-------|-------|
| **Part** | 03g |
| **File** | `backend/app/middleware/logging_middleware.py` |
| **Next** | [Part 03h — rate_limiter.py](./phase4-part03h-rate-limiter.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~10 minutes |
| **Lines** | ~65 lines |

---

## What Does Logging Middleware Do?

Logs EVERY HTTP request with:
- Method (GET, POST, PUT, DELETE)
- Path (/api/v1/habits)
- Status code (200, 404, 500)
- Duration in milliseconds (45.2ms)
- Client IP
- Unique request_id (for tracing one request across all logs)

**Why request_id?** When a user reports "the app is slow," you need to find THAT specific request in millions of log entries. The request_id lets you trace it:

```json
{"event": "http_request", "request_id": "a1b2c3d4", "method": "GET", "path": "/api/v1/analytics/dashboard", "status": 200, "duration_ms": 152.3}
```

---

## Source Code

> 📁 **File:** `backend/app/middleware/logging_middleware.py`
> Type the full code from the source file

Log level selection:
- `2xx/3xx` → `info` (everything fine)
- `4xx` → `warning` (client error — bad input, unauthorized)
- `5xx` → `error` (server error — OUR bug)

---

## 🎤 Interview Q&A

### Q: "How do you trace requests through your system?"

> "Every request gets a unique 8-character request_id generated in the logging middleware. This ID is: added to ALL log entries for that request, returned in the `X-Request-ID` response header, and available to route handlers via `request.state.request_id`. If a user reports an issue, they can share the request_id from the response header, and I can find every log entry for that exact request — across middleware, service, repository, even Redis calls."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03f](./phase4-part03f-error-handler.md) | | [Part 03h — rate_limiter.py](./phase4-part03h-rate-limiter.md) |
