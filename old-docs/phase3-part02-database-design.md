# 🗄️ Phase 3 — Part 02: Database Design

> **"A well-designed database makes every query fast. A poorly designed one makes every feature painful."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 3 — Low-Level Design |
| **Part** | 02 of 02 |
| **Previous** | [Phase 3 Part 01 — LLD](./phase3-part01-low-level-design.md) |
| **Next** | [Phase 4 Part 01 — Project Skeleton Overview](./phase4-part01-project-skeleton-overview.md) |
| **Time to Read** | ~20 minutes |

---

## ER Diagram

```
┌──────────────────┐
│      users       │
├──────────────────┤
│ id          UUID │ PK
│ email    VARCHAR │ UNIQUE, INDEX
│ password_hash    │
│ full_name        │
│ timezone         │
│ is_active  BOOL  │
│ created_at       │
│ updated_at       │
└───────┬──────────┘
        │ 1:N (one user has many...)
        │
   ┌────┴──────────────────────────────────────────┐
   │         │          │          │                │
   ▼         ▼          ▼          ▼                ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐ ┌──────────────────┐
│ habits │ │  docs  │ │ai_chat │ │ ai_insights │ │ notif_settings   │
├────────┤ ├────────┤ ├────────┤ ├─────────────┤ ├──────────────────┤
│id   PK │ │id   PK │ │id   PK │ │id        PK │ │id             PK │
│user_id │ │user_id │ │user_id │ │user_id   FK │ │user_id FK UNIQUE│
│name    │ │filename│ │role    │ │insight_type │ │daily_reminder    │
│type    │ │status  │ │content │ │title       │ │weekly_report     │
│unit    │ │chunks  │ │tokens  │ │content     │ │streak_alerts     │
│target  │ └───┬────┘ └────────┘ │tokens      │ │reminder_time     │
│color   │     │ 1:N             └─────────────┘ └──────────────────┘
│icon    │     ▼
│order   │ ┌──────────────┐
│archived│ │doc_chunks    │
└───┬────┘ ├──────────────┤
    │ 1:N  │id         PK │
    ▼      │document_id FK│
┌────────┐ │user_id    FK │
│hab_logs│ │chunk_text    │
├────────┤ │chunk_index   │
│id   PK │ │page_number   │
│user_id │ │token_count   │
│habit_id│ │embedding     │
│log_date│ │ vector(768)  │
│val_num │ └──────────────┘
│val_bool│
│val_scl │
│notes   │
└────────┘
 UNIQUE(user_id, habit_id, log_date)
```

---

## 8 Tables Explained

| Table | Rows (est. 1yr) | Key Query | Index Strategy |
|-------|-----------------|-----------|---------------|
| **users** | ~1,000 | Login by email | `email` UNIQUE |
| **habits** | ~5,000 | Active habits per user | `(user_id, is_archived)` |
| **habit_logs** | ~500,000 | Today's logs, date range, streaks | `(user_id, log_date)`, `(habit_id, log_date)`, UNIQUE constraint |
| **documents** | ~5,000 | List per user | `user_id` |
| **document_chunks** | ~50,000 | Vector similarity search | IVFFlat on `embedding` |
| **ai_chat_messages** | ~200,000 | Recent history per user | `(user_id, created_at)` |
| **ai_insights** | ~10,000 | List per user | `user_id` |
| **notification_settings** | ~1,000 | Get per user | `user_id` UNIQUE |

---

## 5 Key Design Decisions

### 1. UUID Primary Keys (not auto-increment)

```
Auto-increment: id = 1, 2, 3, 4, 5...
  PROBLEM: Competitor visits /api/v1/users/500 → knows you have ~500 users
  PROBLEM: Can't merge databases (both have id=1)

UUID: id = "550e8400-e29b-41d4-a716-446655440000"
  SAFE: Expose in URLs without info leakage
  SAFE: Merge databases (globally unique)
  SAFE: Generate on client OR server
```

### 2. Soft Delete for Habits (is_archived)

```
Hard delete: DELETE FROM habits WHERE id = :id
  PROBLEM: All historical analytics referencing this habit break
  PROBLEM: "You drank avg 8 glasses when you tracked water" → can't calculate

Soft delete: UPDATE habits SET is_archived = true WHERE id = :id
  SAFE: Historical data preserved
  SAFE: Analytics still work
  SAFE: User can potentially restore later
  QUERY: WHERE is_archived = false (filter in every query)
```

### 3. Three Value Columns (not one JSONB)

```
Option A — One JSONB column:
  {"value": 8.0}  or  {"value": true}  or  {"value": 7}
  PROBLEM: No type safety at DB level
  PROBLEM: Can't use SUM(value) directly
  PROBLEM: "true" and 1 and "1" all look different

Option B — Three typed columns (OUR CHOICE):
  value_numeric FLOAT   → 8.0 (water glasses)
  value_boolean BOOL    → true (did exercise)
  value_scale   INT     → 7 (mood rating)
  SAFE: Type safety at database level
  SAFE: SUM(value_numeric) works directly
  SAFE: CHECK constraint possible (value_scale BETWEEN 1 AND 10)
```

### 4. UNIQUE Constraint on Logs

```
UNIQUE(user_id, habit_id, log_date)

WHY: Prevents logging "Water" twice on September 26.
  First insert: succeeds
  Second insert: PostgreSQL raises IntegrityError
  Our code: catches error → returns friendly "use update instead"

WHY at DB level (not just application level):
  Two concurrent requests could both check "no existing log" → both insert.
  The DB constraint is the ONLY reliable way to prevent duplicates.
```

### 5. pgvector in Same Database

```
Option A: PostgreSQL + Pinecone (separate vector DB)
  COST: $70/month for Pinecone
  COMPLEXITY: Two databases to manage, backup, scale
  PROBLEM: Document insert and chunk insert are NOT transactional

Option B: PostgreSQL + pgvector (OUR CHOICE)
  COST: $0 (PostgreSQL extension)
  COMPLEXITY: One database
  TRANSACTIONAL: document + chunks committed together
  GOOD ENOUGH: IVFFlat handles ~1M vectors with 95% recall
  UPGRADE PATH: Switch to Pinecone if > 10M vectors
```

---

## Index Strategy

| Index | Type | Query Pattern | Why |
|-------|------|--------------|-----|
| `users.email` | UNIQUE B-tree | `WHERE email = :email` | Login lookup |
| `habits(user_id, is_archived)` | Composite B-tree | `WHERE user_id = :uid AND is_archived = false` | Dashboard habit list |
| `habit_logs(user_id, log_date)` | Composite B-tree | `WHERE user_id = :uid AND log_date = :date` | Daily check-in |
| `habit_logs(habit_id, log_date)` | Composite B-tree | `WHERE habit_id = :hid ORDER BY log_date` | Streak calculation |
| `UNIQUE(user_id, habit_id, log_date)` | Unique constraint | INSERT duplicate detection | Prevent double logs |
| `document_chunks.embedding` | IVFFlat (pgvector) | `ORDER BY embedding <=> query LIMIT 5` | RAG similarity search |
| `ai_chat_messages(user_id, created_at)` | Composite B-tree | `WHERE user_id = :uid ORDER BY created_at DESC` | Chat history |

**Rule of thumb:** Create indexes for columns in WHERE and ORDER BY clauses of your most frequent queries. Every index speeds reads but slows writes (index must be updated on INSERT/UPDATE).

---

## 🎤 Interview Q&A

### Q: "Walk me through your database design"

> "8 tables centered around the users table. Each user has habits, daily habit logs, uploaded documents (with chunk embeddings for RAG), chat messages, insights, and notification settings. The key design decisions: UUID primary keys for security and future sharding, soft delete for habits to preserve analytics, three typed value columns for log entries instead of JSONB for type safety, a UNIQUE constraint on (user_id, habit_id, log_date) enforced at the database level for guaranteed no duplicate logs, and pgvector in the same PostgreSQL instance instead of a separate vector database."

### Q: "Why not use MongoDB for this?"

> "The data is highly relational — habits belong to users, logs reference habits, analytics join across multiple tables. SQL window functions (for streaks) and aggregate queries (for weekly comparisons) are the core of the analytics module. MongoDB doesn't support window functions and would require application-side joins. PostgreSQL gives me relational queries AND vector search (pgvector) in one database. The one case where I'd use MongoDB: if the schema was truly unstructured and changed frequently — but habit tracking has a very stable schema."

### Q: "How do you handle the N+1 query problem?"

> "I don't use lazy loading. Each repository method makes explicit queries — if I need habits with their logs, I write a JOIN query, not 'load habits, then for each habit load logs.' SQLAlchemy's `selectin` loading strategy can batch-load relationships when needed. For the analytics module, I use raw SQL with CTEs and window functions — one query computes the entire streak calculation, not N+1 queries. The key principle: every API endpoint should make a known, bounded number of database queries."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Phase 3 Part 01 — LLD](./phase3-part01-low-level-design.md) | | [Phase 4 Part 01 — Project Skeleton](./phase4-part01-project-skeleton-overview.md) |
