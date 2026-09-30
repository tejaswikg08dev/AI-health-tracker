# 🔒 Phase 9 Part 01: Nginx Reverse Proxy & Monitoring

> **"Nginx sits in front of FastAPI handling 5 responsibilities: reverse proxy (/api → backend), rate limiting (3 zones: general 30r/s, AI 2r/s, login 5r/m), security headers (XSS, clickjacking, MIME sniffing), gzip compression, and SSE support for AI streaming. Plus JSON error pages for 429/502/504."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 9 — Infrastructure & Monitoring |
| **Previous** | [Phase 8 Part 04: Lambda Deployment](./phase8-part04-deployment-lambda.md) |
| **Next** | [Phase 10 Part 01: E2E Curl Commands](./phase10-part01-e2e-curl-commands.md) |
| **Files in This Doc** | 1 file (nginx/default.conf) |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (Nginx config syntax, rate limiting math, proxy headers) |

---

## 1. Why Nginx?

```
WITHOUT Nginx:
  Browser → :8000 → FastAPI (handles EVERYTHING)
  - No rate limiting → one user can flood the server
  - No security headers → vulnerable to XSS/clickjacking
  - No gzip → 100KB JSON responses sent uncompressed
  - No static file serving → React needs separate server

WITH Nginx:
  Browser → :80 → Nginx → :8000 → FastAPI (handles only business logic)
  - Rate limiting at the door (before requests reach Python)
  - Security headers on every response
  - Gzip compresses responses (100KB → 15KB)
  - Static React files served directly (no Python involved)
```

---

## 2. `nginx/default.conf` — Full Source

### Type This Code:

```nginx
# ── Upstream Backend ──
upstream backend {
    server backend:8000;
    keepalive 32;
}

# ── Rate Limiting Zones ──
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=ai_limit:10m rate=2r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;


server {
    listen 80;
    server_name localhost;

    # ── Security Headers ──
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ── Gzip Compression ──
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/json
        application/javascript
        application/xml
        image/svg+xml;

    # ── API Routes → Backend ──
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # ── AI Endpoints (Stricter Rate Limit + SSE) ──
    location /api/v1/ai/ {
        limit_req zone=ai_limit burst=5 nodelay;

        proxy_pass http://backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE (Server-Sent Events) support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # ── Login (Anti-Brute-Force) ──
    location /api/v1/auth/login {
        limit_req zone=login_limit burst=3 nodelay;

        proxy_pass http://backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # ── Health Check ──
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }

    # ── Frontend Static Files ──
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;

        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }
    }

    # ── API Docs ──
    location /docs {
        proxy_pass http://backend/docs;
        proxy_set_header Host $host;
    }
    location /redoc {
        proxy_pass http://backend/redoc;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://backend/openapi.json;
        proxy_set_header Host $host;
    }

    # ── Custom JSON Error Pages ──
    error_page 429 @rate_limited;
    location @rate_limited {
        default_type application/json;
        return 429 '{"error_code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please slow down.", "detail": null}';
    }

    error_page 502 @bad_gateway;
    location @bad_gateway {
        default_type application/json;
        return 502 '{"error_code": "SERVICE_UNAVAILABLE", "message": "Backend service is starting up. Please try again in a moment.", "detail": null}';
    }

    error_page 504 @gateway_timeout;
    location @gateway_timeout {
        default_type application/json;
        return 504 '{"error_code": "GATEWAY_TIMEOUT", "message": "Request timed out. Please try again.", "detail": null}';
    }
}
```

---

## 3. Rate Limiting — Three Zones Explained

| Zone | Rate | Burst | Protects Against |
|------|------|-------|-----------------|
| `api_limit` | 30 req/sec per IP | 20 | General API abuse, scrapers |
| `ai_limit` | 2 req/sec per IP | 5 | Expensive LLM calls ($0.01-0.05 each) |
| `login_limit` | 5 req/min per IP | 3 | Password brute-force attacks |

**How `burst` works:**
```
rate=30r/s, burst=20:
  - Normal: 30 requests/second are processed
  - Burst: up to 20 EXTRA requests are queued (not rejected)
  - nodelay: queued requests are processed immediately
  - Request #51 in a second: rejected with 429

rate=5r/m (login):
  - 5 login attempts per minute per IP
  - Burst of 3: allows 8 rapid attempts, then blocks
  - Attacker needs 200 seconds to try 100 passwords (vs 1 second without)
```

**`$binary_remote_addr`** — The client's IP address in binary format (saves memory vs string). 10 MB zone stores ~160,000 IP addresses. More than enough for any single server.

---

## 4. Security Headers

| Header | Value | Prevents |
|--------|-------|----------|
| `X-Frame-Options` | `SAMEORIGIN` | **Clickjacking** — can't embed in iframe on other sites |
| `X-Content-Type-Options` | `nosniff` | **MIME sniffing** — browser trusts our Content-Type |
| `X-XSS-Protection` | `1; mode=block` | **XSS** — browser stops rendering on detected XSS |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | **Info leak** — don't send full URL to other domains |

---

## 5. SSE Support for AI Streaming

```nginx
location /api/v1/ai/ {
    proxy_buffering off;          # Send data to client IMMEDIATELY
    proxy_cache off;              # Don't cache streaming responses
    proxy_read_timeout 300s;      # AI can take up to 5 minutes
    chunked_transfer_encoding on; # Allow chunked responses
}
```

Without `proxy_buffering off`, Nginx collects the entire response before sending it to the client. For AI streaming (word-by-word), this would negate the streaming — the user would wait for the complete response, then see it all at once.

---

## 6. Monitoring: What to Track

### Application-Level Metrics (FastAPI + structlog)

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Request latency (p95) | structlog timing | > 2s for API, > 30s for AI |
| Error rate (5xx) | structlog errors | > 1% of requests |
| Active users | JWT decode count | Informational |
| AI token usage | token_tracker.py | > 100K tokens/day |
| Cache hit rate | Redis stats | < 80% (cache is stale) |

### Infrastructure Metrics (Docker / AWS)

| Metric | Tool | Alert Threshold |
|--------|------|----------------|
| CPU usage | Docker stats / CloudWatch | > 80% sustained |
| Memory usage | Docker stats / CloudWatch | > 85% |
| Disk usage | `df -h` / CloudWatch | > 90% |
| DB connections | PostgreSQL `pg_stat_activity` | > 80% of pool |
| Redis memory | `redis-cli INFO memory` | > 90% of maxmemory |

### Health Check Endpoint

```python
# Already in your app/main.py:
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

Nginx proxies `/health` to the backend with `access_log off` — health checks happen every 30 seconds, no need to fill logs with them.

---

## 7. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **Reverse proxy** | Nginx forwards `/api` to FastAPI |
| 2 | **3-zone rate limiting** | General (30r/s), AI (2r/s), Login (5r/m) |
| 3 | **`burst` + `nodelay`** | Queue excess requests instead of rejecting |
| 4 | **Security headers** | XSS, clickjacking, MIME sniffing prevention |
| 5 | **Gzip compression** | 100KB → 15KB (comp_level 6) |
| 6 | **`proxy_buffering off`** | Required for SSE streaming |
| 7 | **`try_files $uri /index.html`** | SPA routing — all paths serve React |
| 8 | **JSON error pages** | 429/502/504 return API-format JSON |
| 9 | **`keepalive 32`** | Connection pooling to backend |
| 10 | **`X-Request-ID`** | Request tracing through proxy chain |

---

## 8. Interview Questions

### Q1: "Why Nginx in front of FastAPI?"

**A:** Five reasons: (1) **Rate limiting** at the network edge before requests reach Python — cheaper than FastAPI middleware. (2) **Security headers** applied to ALL responses including errors. (3) **Gzip compression** — Nginx is written in C, compresses faster than Python. (4) **Static file serving** — React files served directly without touching Python. (5) **SSE support** — `proxy_buffering off` enables streaming for AI chat. In production, Nginx handles 10K+ concurrent connections with minimal RAM via its event-driven architecture.

### Q2: "How does rate limiting prevent brute-force attacks?"

**A:** The login endpoint is limited to 5 requests per minute per IP with a burst of 3. An attacker trying 1000 passwords would need ~200 minutes instead of ~1 second. Combined with bcrypt (which takes ~250ms per verify), brute-forcing a 12-character password becomes computationally infeasible. If the attacker uses multiple IPs (distributed attack), we'd add CAPTCHA or account lockout at the application layer.

---

## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 8 Part 04: Lambda Deployment](./phase8-part04-deployment-lambda.md) |
| ➡️ Next | [Phase 10 Part 01: E2E Curl Commands](./phase10-part01-e2e-curl-commands.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**🎉 Phase 9 (Nginx & Monitoring) is COMPLETE.**

*One config file, five responsibilities: reverse proxy, rate limiting, security headers, compression, and SSE streaming. JSON error pages for a consistent API experience. Next: end-to-end testing and interview preparation.*
