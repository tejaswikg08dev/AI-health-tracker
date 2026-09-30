# Database Design — Health Tracker

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
└──────┬───────────┘
       │ 1:N
       │
  ┌────┴──────────────────────────────────────────────┐
  │            │            │           │              │
  ▼            ▼            ▼           ▼              ▼
┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────────┐ ┌─────────────────┐
│  habits  │ │documents │ │ai_chat_ │ │ai_insights │ │notification_    │
│          │ │          │ │messages │ │            │ │settings         │
├──────────┤ ├──────────┤ ├─────────┤ ├────────────┤ ├─────────────────┤
│id     PK │ │id     PK │ │id    PK │ │id       PK │ │id            PK │
│user_id FK│ │user_id FK│ │user_id  │ │user_id  FK │ │user_id FK UNIQ │
│name      │ │filename  │ │role     │ │insight_type│ │daily_reminder   │
│habit_type│ │file_type │ │content  │ │title       │ │weekly_report    │
│unit      │ │status    │ │tokens   │ │content     │ │streak_alerts    │
│target    │ │chunk_cnt │ │created  │ │tokens      │ │reminder_time    │
│color     │ │s3_key    │ └─────────┘ │created     │ └─────────────────┘
│icon      │ │created   │             └────────────┘
│sort_order│ └────┬─────┘
│is_archived│      │ 1:N
│created_at│      ▼
└────┬─────┘ ┌────────────────┐
     │ 1:N   │document_chunks │
     ▼       ├────────────────┤
┌──────────┐ │id           PK │
│habit_logs│ │document_id  FK │
├──────────┤ │user_id      FK │
│id     PK │ │chunk_text      │
│user_id FK│ │chunk_index     │
│habit_id  │ │page_number     │
│log_date  │ │token_count     │
│val_num   │ │embedding       │ ← vector(768)
│val_bool  │ │  vector(768)   │
│val_scale │ │created_at      │
│notes     │ └────────────────┘
│created_at│
└──────────┘
  UNIQUE(user_id, habit_id, log_date)
```

## Tables Summary

| Table | Rows (est. 1 year) | Key Queries |
|-------|-------------------|-------------|
| users | ~1 per user | Login (by email), profile (by id) |
| habits | ~5-10 per user | List active (by user_id, is_archived) |
| habit_logs | ~1,500 per user/year | Daily (user+date), range (user+date range), streaks (habit+date) |
| documents | ~5-20 per user | List (by user_id) |
| document_chunks | ~100-500 per user | Vector search (embedding <=> query) |
| ai_chat_messages | ~500-2,000 per user/year | History (user_id, created_at DESC) |
| ai_insights | ~50-100 per user/year | List (user_id, created_at DESC) |
| notification_settings | 1 per user | Get/Update (by user_id) |

## Index Strategy

| Index | Type | Purpose | Query |
|-------|------|---------|-------|
| `users.email` | UNIQUE B-tree | Login lookup | `WHERE email = ?` |
| `habits(user_id, is_archived)` | Composite B-tree | Dashboard habit list | `WHERE user_id = ? AND is_archived = false` |
| `habit_logs(user_id, log_date)` | Composite B-tree | Daily check-in | `WHERE user_id = ? AND log_date = ?` |
| `habit_logs(habit_id, log_date)` | Composite B-tree | Streak calculation | `WHERE habit_id = ? ORDER BY log_date` |
| `UNIQUE(user_id, habit_id, log_date)` | Unique constraint | Prevent duplicate logs | INSERT duplicate detection |
| `document_chunks.embedding` | IVFFlat (pgvector) | RAG similarity search | `ORDER BY embedding <=> query LIMIT 5` |
| `ai_chat_messages(user_id, created_at)` | Composite B-tree | Chat history | `WHERE user_id = ? ORDER BY created_at DESC` |

## Key Design Decisions

**1. UUID Primary Keys (not auto-increment)**
- Safe to expose in URLs and APIs
- No information leakage (can't guess user count)
- Supports future database sharding

**2. Soft Delete for Habits (is_archived)**
- Historical analytics still reference archived habits
- User can potentially restore later
- Hard delete only for logs (user correcting mistakes)

**3. Three Value Columns (not one polymorphic column)**
- `value_numeric` FLOAT, `value_boolean` BOOL, `value_scale` INT
- Type safety at the database level
- Clear semantics: each column only stores its type
- Alternative: single JSONB column — more flexible but loses type safety

**4. pgvector in Same Database (not separate vector DB)**
- One database to manage, backup, and scale
- Transactional: document + chunks in same commit
- IVFFlat index for approximate nearest neighbor search
- Good for < 1M vectors; consider Pinecone at 10M+

**5. Unique Constraint on Logs (not application-level check)**
- `UNIQUE(user_id, habit_id, log_date)` enforced by PostgreSQL
- Even if two requests arrive simultaneously, database prevents duplicates
- Application checks first (friendly error), DB constraint is the safety net
