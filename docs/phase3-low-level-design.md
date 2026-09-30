# 🔧 Phase 3: Low-Level Design (LLD)

> **"LLD is where you show HOW things work internally — algorithms, class structures, and the exact shape of every function."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 3 — Low-Level Design |
| **Previous** | [phase2-high-level-design.md](./phase2-high-level-design.md) |
| **Next** | [phase4-part01-project-setup-docker.md](./phase4-part01-project-setup-docker.md) |
| **Time to Read** | ~45 minutes |

---

## 📖 Table of Contents

1. [Module Layer Pattern](#layer-pattern)
2. [All SQLAlchemy Model Signatures](#model-signatures)
3. [All Repository Method Signatures](#repository-signatures)
4. [All Service Method Signatures](#service-signatures)
5. [All Router Endpoint Signatures](#router-signatures)
6. [Key Algorithms](#key-algorithms)
7. [Alembic Migration Summary](#migration-summary)
8. [What You Learned](#what-you-learned)

---

<a name="layer-pattern"></a>
## 1. Module Layer Pattern

Every module in our app follows this EXACT layered structure (same as Spring Boot's Controller → Service → Repository):

```
┌─────────────────────────────────────────────┐
│              ROUTER (HTTP Layer)              │
│  FastAPI APIRouter with @router.get/post     │
│  - Parses request, extracts user_id from JWT │
│  - Calls service, formats HTTP response      │
│  - Knows about: HTTP status codes, headers   │
│  - Does NOT know: business rules, SQL        │
├─────────────────────────────────────────────┤
│             SERVICE (Business Logic)          │
│  Plain Python class instantiated per-request │
│  - Validates business rules                  │
│  - Orchestrates one or more repositories     │
│  - Raises domain exceptions                  │
│  - Knows about: business rules, validation   │
│  - Does NOT know: HTTP, SQL syntax           │
├─────────────────────────────────────────────┤
│           REPOSITORY (Data Access)            │
│  Extends BaseRepository[ModelType]           │
│  - Executes SQL via SQLAlchemy               │
│  - Returns model objects                     │
│  - Knows about: SQL, database, indexes       │
│  - Does NOT know: business rules, HTTP       │
├─────────────────────────────────────────────┤
│              MODELS (Database Schema)         │
│  SQLAlchemy classes inheriting from Base     │
│  - Defines table structure                   │
├─────────────────────────────────────────────┤
│            SCHEMAS (API Validation)           │
│  Pydantic BaseModel classes                  │
│  - Request validation, response formatting   │
├─────────────────────────────────────────────┤
│           EXCEPTIONS (Domain Errors)          │
│  Inherits from shared exceptions             │
│  - Each maps to an HTTP status code          │
└─────────────────────────────────────────────┘
```

**Python/FastAPI mapping to Spring Boot:**

| Spring Boot | Python/FastAPI |
|-------------|---------------|
| `@RestController` | `router = APIRouter()` |
| `@Service` | `class AuthService:` |
| `JpaRepository<User, String>` | `class UserRepository(BaseRepository[User]):` |
| `@Entity` | `class User(Base):` |
| DTO + MapStruct | `class UserResponse(BaseSchema):` |
| `@ExceptionHandler` | `register_error_handlers(app)` |
| `@Autowired` | `Depends(get_async_session)` |

---

<a name="model-signatures"></a>
## 2. All SQLAlchemy Model Signatures

### Auth Module Models

```python
# backend/app/modules/auth/models.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID]           # PK, default=uuid4
    email: Mapped[str]              # unique, indexed, VARCHAR(255)
    password_hash: Mapped[str]      # bcrypt output, VARCHAR(255)
    full_name: Mapped[str]          # VARCHAR(100)
    timezone: Mapped[str]           # default="UTC", VARCHAR(50)
    is_active: Mapped[bool]         # default=True (soft delete)
    created_at: Mapped[datetime]    # auto-set on creation
    updated_at: Mapped[datetime | None]  # auto-set on update
```

### Habits Module Models

```python
# backend/app/modules/habits/models.py
class Habit(Base):
    __tablename__ = "habits"
    id: Mapped[uuid.UUID]           # PK
    user_id: Mapped[uuid.UUID]      # FK → users.id, indexed
    name: Mapped[str]               # VARCHAR(100)
    habit_type: Mapped[str]         # "numeric" | "boolean" | "scale"
    unit: Mapped[str]               # default="", VARCHAR(50)
    target_value: Mapped[float | None]  # nullable (boolean/scale have no target)
    color: Mapped[str]              # default="#3B82F6", VARCHAR(7)
    icon: Mapped[str]               # default="⭐", VARCHAR(50)
    sort_order: Mapped[int]         # default=0 (drag-and-drop order)
    is_archived: Mapped[bool]       # default=False (soft delete)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime | None]
```

### Logs Module Models

```python
# backend/app/modules/logs/models.py
class HabitLog(Base):
    __tablename__ = "habit_logs"
    __table_args__ = (UniqueConstraint("user_id", "habit_id", "log_date", name="uq_user_habit_date"),)

    id: Mapped[uuid.UUID]           # PK
    user_id: Mapped[uuid.UUID]      # FK → users.id, indexed
    habit_id: Mapped[uuid.UUID]     # FK → habits.id, indexed
    log_date: Mapped[date]          # indexed (daily + range queries)
    value_numeric: Mapped[float | None]    # for numeric habits
    value_boolean: Mapped[bool | None]     # for boolean habits
    value_scale: Mapped[int | None]        # for scale habits (1-10)
    notes: Mapped[str | None]       # VARCHAR(500)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime | None]
```

### AI Module Models

```python
# backend/app/modules/ai/models.py

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]      # FK → users.id
    filename: Mapped[str]           # VARCHAR(255)
    file_type: Mapped[str]          # "pdf", "txt", "md"
    file_size: Mapped[int]          # bytes
    page_count: Mapped[int | None]  # PDF only
    status: Mapped[str]             # "uploaded" → "processing" → "processed" | "failed"
    chunk_count: Mapped[int]        # default=0
    error_message: Mapped[str | None]
    s3_key: Mapped[str | None]      # MinIO/S3 object key
    created_at: Mapped[datetime]

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID]
    document_id: Mapped[uuid.UUID]  # FK → documents.id
    user_id: Mapped[uuid.UUID]      # FK → users.id
    chunk_text: Mapped[str]         # TEXT
    chunk_index: Mapped[int]        # order within document
    page_number: Mapped[int | None] # PDF page number
    token_count: Mapped[int]        # for context window management
    # embedding: vector(768)        # pgvector column (created in migration SQL)
    created_at: Mapped[datetime]

class AiChatMessage(Base):
    __tablename__ = "ai_chat_messages"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]
    role: Mapped[str]               # "user" | "assistant"
    content: Mapped[str]            # TEXT
    tokens_used: Mapped[int]
    created_at: Mapped[datetime]

class AiInsight(Base):
    __tablename__ = "ai_insights"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]
    insight_type: Mapped[str]       # "weekly_report" | "on_demand" | "streak_milestone"
    title: Mapped[str]              # VARCHAR(200)
    content: Mapped[str]            # TEXT (markdown)
    tokens_used: Mapped[int]
    created_at: Mapped[datetime]
```

### Notifications Module Models

```python
# backend/app/modules/notifications/models.py
class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]      # FK → users.id, UNIQUE
    daily_reminder: Mapped[bool]    # default=True
    weekly_report: Mapped[bool]     # default=True
    streak_alerts: Mapped[bool]     # default=True
    reminder_time: Mapped[str]      # "HH:MM" format, default="08:00"
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime | None]
```

---

<a name="repository-signatures"></a>
## 3. All Repository Method Signatures

### BaseRepository[T] (inherited by all)

```python
class BaseRepository(Generic[ModelType]):
    async def create(**kwargs) -> ModelType
    async def get_by_id(id: UUID) -> ModelType | None
    async def get_all(offset: int, limit: int) -> list[ModelType]
    async def count() -> int
    async def update(id: UUID, **kwargs) -> ModelType | None
    async def delete(id: UUID) -> bool
```

### Auth

```python
class UserRepository(BaseRepository[User]):
    async def get_by_email(email: str) -> User | None
    async def get_active_by_id(user_id: UUID) -> User | None
    async def email_exists(email: str) -> bool
```

### Habits

```python
class HabitRepository(BaseRepository[Habit]):
    async def get_user_habits(user_id: UUID, include_archived: bool = False) -> list[Habit]
    async def get_user_habit(user_id: UUID, habit_id: UUID) -> Habit | None
    async def name_exists_for_user(user_id: UUID, name: str, exclude_habit_id: UUID | None) -> bool
    async def count_active_habits(user_id: UUID) -> int
    async def get_next_sort_order(user_id: UUID) -> int
    async def reorder_habits(user_id: UUID, habit_ids: list[UUID]) -> None
    async def archive_habit(user_id: UUID, habit_id: UUID) -> Habit | None
```

### Logs

```python
class LogRepository(BaseRepository[HabitLog]):
    async def get_logs_for_date(user_id: UUID, log_date: date) -> list[HabitLog]
    async def get_logs_for_range(user_id: UUID, start: date, end: date, habit_id: UUID | None) -> list[HabitLog]
    async def get_existing_log(user_id: UUID, habit_id: UUID, log_date: date) -> HabitLog | None
    async def get_user_log(user_id: UUID, log_id: UUID) -> HabitLog | None
    async def count_logs_for_date(user_id: UUID, log_date: date) -> int
    async def get_habit_log_dates(user_id: UUID, habit_id: UUID, start: date, end: date) -> list[date]
    async def delete_user_log(user_id: UUID, log_id: UUID) -> bool
```

### Analytics (raw SQL — not ORM)

```python
class AnalyticsRepository:
    async def get_streaks(user_id: UUID) -> list[dict]                    # Window functions, CTEs
    async def get_weekly_summary(user_id: UUID) -> list[dict]             # CASE WHEN inside AVG
    async def get_monthly_trend(user_id: UUID, habit_id: UUID | None, days: int) -> list[dict]  # generate_series
    async def get_completion_rates(user_id: UUID, days: int) -> list[dict]  # GREATEST for date math
    async def get_correlation_data(user_id: UUID, days: int) -> list[dict]  # Self-join
    async def get_today_progress(user_id: UUID) -> dict                    # COUNT subqueries
    async def get_week_completion(user_id: UUID) -> float                  # AVG of daily rates
```

---

<a name="service-signatures"></a>
## 4. All Service Method Signatures

### Auth

```python
class AuthService:
    async def register(data: UserCreate) -> User
    async def login(email: str, password: str) -> TokenResponse
    async def refresh_tokens(refresh_token: str) -> TokenResponse
    async def logout(access_token: str, refresh_token: str | None) -> None
    async def get_current_user(user_id: UUID) -> User
    async def update_profile(user_id: UUID, data: UserUpdate) -> User
```

### Habits

```python
class HabitService:
    async def create_habit(user_id: UUID, data: HabitCreate) -> Habit
    async def get_habits(user_id: UUID, include_archived: bool) -> list[Habit]
    async def get_habit(user_id: UUID, habit_id: UUID) -> Habit
    async def update_habit(user_id: UUID, habit_id: UUID, data: HabitUpdate) -> Habit
    async def delete_habit(user_id: UUID, habit_id: UUID) -> Habit
    async def reorder_habits(user_id: UUID, habit_ids: list[UUID]) -> list[Habit]
```

### Logs

```python
class LogService:
    async def create_log(user_id: UUID, data: LogCreate) -> HabitLog
    async def bulk_create_logs(user_id: UUID, data: BulkLogCreate) -> list[HabitLog]
    async def get_logs_for_date(user_id: UUID, log_date: date) -> list[HabitLog]
    async def get_logs_for_range(user_id: UUID, start: date, end: date, habit_id: UUID | None) -> list[HabitLog]
    async def update_log(user_id: UUID, log_id: UUID, data: LogUpdate) -> HabitLog
    async def delete_log(user_id: UUID, log_id: UUID) -> None
```

### Analytics

```python
class AnalyticsService:
    async def get_dashboard(user_id: UUID) -> DashboardData
    async def get_streaks(user_id: UUID) -> AllStreaksResponse
    async def get_weekly_summary(user_id: UUID) -> WeeklySummaryResponse
    async def get_monthly_trend(user_id: UUID, habit_id: UUID | None, days: int) -> MonthlyTrendResponse
    async def get_completion_rates(user_id: UUID, days: int) -> CompletionRateResponse
    async def get_correlations(user_id: UUID, days: int) -> CorrelationResponse
    # Private: _pearson_correlation(x, y) -> float | None
```

### AI

```python
class AiService:
    async def chat(user_id: UUID, user_name: str, message: str, use_agent: bool) -> str
    async def stream_chat(user_id: UUID, user_name: str, message: str) -> AsyncGenerator[str, None]
    async def get_chat_history(user_id: UUID, limit: int) -> list[AiChatMessage]
    async def upload_document(user_id: UUID, filename: str, file_type: str, content: bytes, size: int) -> Document
    async def get_documents(user_id: UUID) -> list[Document]
    async def delete_document(user_id: UUID, document_id: UUID) -> bool
    async def generate_insight(user_id: UUID) -> AiInsight
    async def get_insights(user_id: UUID, limit: int) -> list[AiInsight]
    async def generate_weekly_report(user_id: UUID, user_name: str) -> AiInsight
```

---

<a name="router-signatures"></a>
## 5. All Router Endpoint Signatures

```python
# Auth: /api/v1/auth
POST   /signup           → 201 UserResponse
POST   /login            → 200 TokenResponse
POST   /refresh          → 200 TokenResponse
POST   /logout           → 200 SuccessResponse
GET    /me               → 200 UserResponse
PUT    /me               → 200 UserResponse

# Habits: /api/v1/habits
POST   /                 → 201 HabitResponse
GET    /                 → 200 list[HabitResponse]
PUT    /reorder          → 200 list[HabitResponse]
GET    /{id}             → 200 HabitResponse
PUT    /{id}             → 200 HabitResponse
DELETE /{id}             → 200 SuccessResponse

# Logs: /api/v1/logs
POST   /                 → 201 LogResponse
POST   /bulk             → 201 list[LogResponse]
GET    /                 → 200 list[LogResponse]     (query: date, start, end, habit_id)
PUT    /{id}             → 200 LogResponse
DELETE /{id}             → 200 SuccessResponse

# Analytics: /api/v1/analytics
GET    /dashboard        → 200 DashboardData
GET    /streaks          → 200 AllStreaksResponse
GET    /weekly-summary   → 200 WeeklySummaryResponse
GET    /monthly-trend    → 200 MonthlyTrendResponse  (query: habit_id, days)
GET    /completion-rate  → 200 CompletionRateResponse (query: days)
GET    /correlations     → 200 CorrelationResponse    (query: days)

# AI: /api/v1/ai
POST   /chat             → 200 {response: str}
GET    /chat/stream      → SSE StreamingResponse     (query: message)
GET    /chat/history     → 200 ChatHistoryResponse
POST   /documents        → 201 DocumentResponse       (file upload)
GET    /documents        → 200 DocumentListResponse
DELETE /documents/{id}   → 200 SuccessResponse
POST   /insights         → 201 InsightResponse
GET    /insights         → 200 InsightListResponse
POST   /weekly-report    → 201 InsightResponse

# Notifications: /api/v1/notifications
GET    /settings         → 200 NotificationSettingsResponse
PUT    /settings         → 200 NotificationSettingsResponse
POST   /test-email       → 200 SuccessResponse

# Export: /api/v1/export
POST   /csv              → StreamingResponse (file download)
POST   /csv/s3           → 200 ExportResponse  (presigned URL)

# Health
GET    /health           → 200 {status, version, environment}
```

---

<a name="key-algorithms"></a>
## 6. Key Algorithms

### Streak Calculation (Gaps and Islands — SQL)

```sql
-- Input:  Dates: Sep 20, 21, 22, 24, 25, 26
-- Output: Streak 1 (Sep 20-22, 3 days), Streak 2 (Sep 24-26, 3 days, CURRENT)

WITH logged_dates AS (
    SELECT log_date, ROW_NUMBER() OVER (ORDER BY log_date) AS rn
    FROM habit_logs WHERE habit_id = :id AND value IS NOT NULL
),
streaks AS (
    SELECT log_date, log_date - (rn * INTERVAL '1 day') AS grp
    FROM logged_dates
)
SELECT COUNT(*) as length, MIN(log_date) as start, MAX(log_date) as end
FROM streaks GROUP BY grp;

-- Trick: date - row_number = constant for consecutive dates
-- Sep 20-1=Sep 19, Sep 21-2=Sep 19, Sep 22-3=Sep 19 → SAME GROUP
-- Sep 24-4=Sep 20 → DIFFERENT GROUP (gap on Sep 23)
```

### Pearson Correlation (Python)

```python
def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    mean_x, mean_y = sum(x)/n, sum(y)/n
    numerator = sum((xi-mean_x)*(yi-mean_y) for xi,yi in zip(x,y))
    denominator = sqrt(sum((xi-mean_x)**2 for xi in x) * sum((yi-mean_y)**2 for yi in y))
    return numerator/denominator if denominator != 0 else None

# r = +1.0 → perfect positive (sleep↑ = mood↑)
# r = -1.0 → perfect negative (screen_time↑ = sleep↓)
# r = 0.0  → no relationship
# |r| < 0.3 → weak, 0.3-0.7 → moderate, > 0.7 → strong
```

### ReAct Agent Loop (Pseudocode)

```python
def agent.run(user_message):
    memory.add(user_message)
    messages = [system_prompt] + memory.get_messages()

    for iteration in range(MAX_ITERATIONS=5):
        response = LLM.chat(messages, tools=tool_schemas)

        if response.has_tool_calls:
            for tool_call in response.tool_calls:
                result = tools[tool_call.name].execute(**tool_call.args)
                messages.append(tool_result(result))
            continue  # loop: let LLM decide next action

        else:  # LLM gave text response (final answer)
            memory.add(response.content)
            return response.content

    # max iterations: ask for best answer
    return LLM.chat(messages, tools=None).content
```

### Cache-Aside Pattern (Pseudocode)

```python
async def get_dashboard(user_id):
    cached = await redis.get(f"analytics:{user_id}:dashboard")
    if cached:
        return json.loads(cached)  # HIT — 0.1ms

    data = await repo.get_today_progress(user_id)  # MISS — 200ms
    await redis.setex(f"analytics:{user_id}:dashboard", 300, json.dumps(data))
    return data

# Invalidation (on log create/update/delete):
async def _invalidate_cache(user_id):
    await redis.delete(*[key async for key in redis.scan_iter(f"analytics:{user_id}:*")])
```

---

<a name="migration-summary"></a>
## 7. Alembic Migration Summary

| # | Migration File | What It Creates |
|---|---------------|-----------------|
| 001 | `001_create_users_table.py` | `users` table + `pgvector` extension + `uuid-ossp` extension |
| 002 | `002_create_habits_table.py` | `habits` table + indexes on `(user_id)` and `(user_id, is_archived)` |
| 003 | `003_create_habit_logs_table.py` | `habit_logs` table + UNIQUE constraint + 3 indexes |
| 004 | `004_create_ai_tables.py` | `documents`, `document_chunks` (with `vector(768)`), `ai_chat_messages`, `ai_insights` + IVFFlat index |
| 005 | `005_create_notification_settings.py` | `notification_settings` table with `user_id` UNIQUE |

---

<a name="what-you-learned"></a>
## What You Learned

| # | Concept | Key Takeaway |
|---|---------|-------------|
| 1 | Layer pattern | Router → Service → Repository (same as Controller → Service → Repository in Spring) |
| 2 | Model signatures | SQLAlchemy `Mapped[type]` with `mapped_column()` options |
| 3 | Repository pattern | `BaseRepository[T]` gives 6 CRUD methods free. Add custom queries per module. |
| 4 | Service signatures | Business logic methods — validation, orchestration, no SQL or HTTP |
| 5 | Router signatures | FastAPI endpoints — HTTP verbs, paths, response types |
| 6 | Gaps and islands | SQL algorithm for streak calculation using ROW_NUMBER() |
| 7 | Pearson correlation | Statistical formula for measuring habit relationships |
| 8 | ReAct loop | THINK → ACT → OBSERVE → REPEAT (max 5 iterations) |
| 9 | Cache-aside | Check cache → miss → compute → store → return |
| 10 | Migration chain | 5 sequential Alembic migrations creating 8 tables |

---

## 📚 Document Index

| Phase | Document | Status |
|-------|----------|--------|
| 0.1 | [Project Overview](./phase0-part1-project-overview.md) | ✅ |
| 0.2 | [Environment Setup](./phase0-part2-environment-setup.md) | ✅ |
| 1 | [System Design](./phase1-system-design.md) | ✅ |
| 2 | [High-Level Design](./phase2-high-level-design.md) | ✅ |
| **3** | **Low-Level Design** | **← You are here** |
| 4.01 | [Project Setup + Docker](./phase4-part01-project-setup-docker.md) | ⬜ Next |

---
*End of Phase 3: Low-Level Design*
*Next: [Phase 4 Part 01: Project Setup + Docker →](./phase4-part01-project-setup-docker.md)*
