# ⚙️ Phase 3 — Part 01: Low-Level Design (LLD)

> **"LLD is where you show HOW things work internally — algorithms, class structures, and sequence diagrams."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 3 — Low-Level Design |
| **Part** | 01 of 02 |
| **Previous** | [Phase 2 — High-Level Design](./phase2-part01-high-level-design.md) |
| **Next** | [Phase 3 Part 02 — Database Design](./phase3-part02-database-design.md) |
| **Time to Read** | ~25 minutes |

---

## What is LLD?

LLD zooms INTO each component and shows HOW it works:
- What **classes/functions** exist
- What **algorithms** they use
- How **data flows** through them step by step
- **Sequence diagrams** showing the order of operations

---

## LLD 1: Module Layer Pattern

Every module in our app follows this EXACT layered structure:

```
┌─────────────────────────────────────────────┐
│              ROUTER (HTTP Layer)              │
│  - Defines endpoints (GET, POST, PUT, DELETE)│
│  - Parses request, extracts user_id from JWT │
│  - Calls service, formats HTTP response      │
│  - Knows about: HTTP status codes, headers   │
│  - Does NOT know: business rules, SQL        │
├─────────────────────────────────────────────┤
│             SERVICE (Business Logic)          │
│  - Validates business rules                  │
│  - Orchestrates multiple repositories        │
│  - Raises domain exceptions                  │
│  - Knows about: business rules, validation   │
│  - Does NOT know: HTTP, SQL syntax           │
├─────────────────────────────────────────────┤
│           REPOSITORY (Data Access)            │
│  - Executes SQL queries via SQLAlchemy       │
│  - Returns model objects                     │
│  - Knows about: SQL, database, indexes       │
│  - Does NOT know: business rules, HTTP       │
├─────────────────────────────────────────────┤
│              MODELS (Database Schema)         │
│  - Defines table structure (columns, types)  │
│  - SQLAlchemy ORM class                      │
├─────────────────────────────────────────────┤
│             SCHEMAS (Validation)              │
│  - Pydantic models for request/response      │
│  - Validates input, controls output          │
├─────────────────────────────────────────────┤
│            EXCEPTIONS (Error Types)           │
│  - Module-specific error classes             │
│  - Each maps to an HTTP status code          │
└─────────────────────────────────────────────┘
```

**Why separate layers?**
- **Testable:** Test service logic without HTTP. Test repo without business rules.
- **Swappable:** Change PostgreSQL to MongoDB? Only repositories change.
- **Clean:** Each layer has ONE responsibility (Single Responsibility Principle).

---

## LLD 2: Authentication Sequence Diagram

### Login Flow

```
Client              Router              Service           Repository         Redis
  │                   │                   │                  │                │
  │ POST /login       │                   │                  │                │
  │ {email, password} │                   │                  │                │
  │──────────────────>│                   │                  │                │
  │                   │ authenticate()    │                  │                │
  │                   │──────────────────>│                  │                │
  │                   │                   │ get_by_email()   │                │
  │                   │                   │─────────────────>│                │
  │                   │                   │    User object   │                │
  │                   │                   │<─────────────────│                │
  │                   │                   │                  │                │
  │                   │                   │ verify_password() │                │
  │                   │                   │ (bcrypt compare)  │                │
  │                   │                   │                  │                │
  │                   │                   │ create_access_token(user.id)      │
  │                   │                   │ create_refresh_token(user.id)     │
  │                   │                   │                  │                │
  │                   │  TokenResponse    │                  │                │
  │                   │<──────────────────│                  │                │
  │ {access_token,    │                   │                  │                │
  │  refresh_token}   │                   │                  │                │
  │<──────────────────│                   │                  │                │
```

### Token Refresh Flow

```
Client                Router            Service              Redis
  │                     │                 │                    │
  │ POST /refresh       │                 │                    │
  │ {refresh_token}     │                 │                    │
  │────────────────────>│                 │                    │
  │                     │ refresh()       │                    │
  │                     │────────────────>│                    │
  │                     │                 │ decode(token, "refresh")
  │                     │                 │ → extract user_id  │
  │                     │                 │                    │
  │                     │                 │ GET blacklist:token │
  │                     │                 │───────────────────>│
  │                     │                 │    "not found"     │
  │                     │                 │<───────────────────│
  │                     │                 │ (token is valid)   │
  │                     │                 │                    │
  │                     │                 │ SETEX blacklist:old_token TTL
  │                     │                 │───────────────────>│
  │                     │                 │ (blacklist old token)
  │                     │                 │                    │
  │                     │                 │ create_access_token(user.id)
  │                     │                 │ create_refresh_token(user.id)
  │                     │                 │                    │
  │                     │ new tokens      │                    │
  │ {new_access,        │<────────────────│                    │
  │  new_refresh}       │                 │                    │
  │<────────────────────│                 │                    │
```

---

## LLD 3: Streak Calculation Algorithm

### The Problem
Given dates a habit was logged, find consecutive day sequences (streaks).

### Algorithm: Gaps and Islands

```
Input:  Logged dates: Sep 20, 21, 22, 24, 25, 26

Step 1: Number each date with ROW_NUMBER()
  Sep 20 → rn=1
  Sep 21 → rn=2
  Sep 22 → rn=3
  Sep 24 → rn=4  ← gap on Sep 23
  Sep 25 → rn=5
  Sep 26 → rn=6

Step 2: Subtract row_number from date → group identifier
  Sep 20 - 1 day = Sep 19
  Sep 21 - 2 days = Sep 19  ← same group!
  Sep 22 - 3 days = Sep 19  ← same group!
  Sep 24 - 4 days = Sep 20  ← different group (gap!)
  Sep 25 - 5 days = Sep 20
  Sep 26 - 6 days = Sep 20

Step 3: GROUP BY group → COUNT = streak length
  Group Sep 19: 3 days (Sep 20-22)
  Group Sep 20: 3 days (Sep 24-26) ← current streak

Time complexity: O(n log n) — one query with window function
```

---

## LLD 4: Cache-Aside Pattern

```
GET /analytics/dashboard
         │
         ▼
    Check Redis
    Key: analytics:{user_id}:dashboard
         │
    ┌────┴────┐
    │         │
  HIT       MISS
    │         │
    ▼         ▼
  Return    Query PostgreSQL (50-200ms)
  cached    Transform to response schema
  JSON      SET Redis with TTL (5 min)
  (< 1ms)   Return fresh data
    │         │
    └────┬────┘
         │
         ▼
    Response to client


INVALIDATION (when logs change):
  POST /logs → LogService creates log
    → LogService calls: DELETE analytics:{user_id}:*
    → Next dashboard load: cache MISS → fresh data computed
```

---

## LLD 5: ReAct Agent Loop

```
function agent.run(user_message):
    memory.add(user_message)
    messages = [system_prompt] + memory.get_messages()

    for iteration in range(MAX_ITERATIONS=5):
        response = LLM.chat(messages, tools=tool_schemas)

        if response.has_tool_calls:
            for tool_call in response.tool_calls:
                result = tools[tool_call.name].execute(**tool_call.args)
                messages.append(tool_result(result))
            continue  ← loop again: let LLM decide next action

        else:  ← LLM gave text response (final answer)
            memory.add(response.content)
            return response.content

    ← max iterations: ask LLM for best answer with gathered data
    response = LLM.chat(messages, tools=None)
    return response.content
```

---

## LLD 6: Rate Limiter (Sliding Window)

```
Request arrives at /api/v1/habits
  │
  ▼
1. Determine limit: RATE_LIMITS["/api/v1/"] = {requests: 60, window: 60s}
  │
  ▼
2. Build Redis key: "rl:{client_ip}:/api/v1/habits:{window_start}"
   window_start = int(time()) // 60  (changes every 60 seconds)
  │
  ▼
3. INCR key → current_count
  │
  ▼
4. If count == 1: EXPIRE key 60  (first request in this window)
  │
  ▼
5. If count > 60: return HTTP 429 "Too Many Requests"
   Else: proceed to handler
  │
  ▼
6. Add response headers:
   X-RateLimit-Limit: 60
   X-RateLimit-Remaining: 59
```

---

## 🎤 Interview Q&A

### Q: "Explain the layered architecture of your modules"

> "Every module follows Router → Service → Repository. The Router handles HTTP concerns — parsing requests, extracting the JWT user_id, formatting responses. The Service handles business logic — validation rules, orchestrating multiple repositories, raising domain exceptions. The Repository handles data access — SQL queries, connection management. This separation means I can test business logic without HTTP, swap the database without changing business rules, and each layer has exactly one responsibility."

### Q: "How do you calculate streaks?"

> "Using the gaps-and-islands SQL algorithm with window functions. I number each logged date with ROW_NUMBER() ordered by date, then subtract the row number from the date. Consecutive dates produce the SAME group value because date minus sequential integer is constant for consecutive values. I GROUP BY this computed group and COUNT to get streak lengths. The current streak is the group that includes today or yesterday. It's one SQL query with O(n log n) complexity."

### Q: "How does your rate limiter work?"

> "Fixed window counter with Redis. For each request, I build a key combining the client IP, endpoint path, and current time window. INCR increments the counter atomically. If it's the first request (count==1), I set EXPIRE so the key auto-deletes after the window. If count exceeds the limit, I return HTTP 429. Different endpoints get different limits: 30/s for general API, 2/s for AI (expensive LLM calls), 5/minute for login (prevent brute force). If Redis is down, I fail open — requests pass through. Rate limiting is a nice-to-have, not a hard gate."

### Q: "Walk me through the ReAct agent loop"

> "The agent receives a user question and enters a loop. It sends the conversation history plus tool descriptions to the LLM. The LLM either returns a text response (final answer) or requests a tool call. If it requests a tool — say, query_logs — the agent executes the tool against the real database, appends the result to the conversation, and loops back to the LLM. The LLM sees the tool result and decides: need more data? Call another tool. Have enough? Generate the final answer. I cap at 5 iterations to prevent infinite loops. If it hits the cap, I ask for the best answer with whatever data was gathered."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Phase 2 — HLD](./phase2-part01-high-level-design.md) | | [Phase 3 Part 02 — Database Design](./phase3-part02-database-design.md) |
