# SQL Queries — From This Project

Every complex query from the Health Tracker, explained for interviews.

---

## 1. Streak Calculation (Gaps and Islands)

**Interview question:** "How do you calculate consecutive day streaks in SQL?"

```sql
-- Find consecutive days a habit was logged
-- Uses the "gaps and islands" technique with window functions

WITH logged_dates AS (
    SELECT
        log_date,
        ROW_NUMBER() OVER (ORDER BY log_date) AS rn
    FROM habit_logs
    WHERE habit_id = :habit_id
      AND (value_numeric IS NOT NULL OR value_boolean = true OR value_scale IS NOT NULL)
),
streaks AS (
    -- The magic: subtract row_number from date
    -- Consecutive dates produce the SAME group value
    SELECT
        log_date,
        log_date - (rn * INTERVAL '1 day') AS grp
    FROM logged_dates
),
streak_lengths AS (
    SELECT
        COUNT(*) AS streak_length,
        MIN(log_date) AS streak_start,
        MAX(log_date) AS streak_end
    FROM streaks
    GROUP BY grp
)
-- Current streak: includes today or yesterday
SELECT streak_length FROM streak_lengths
WHERE streak_end >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY streak_end DESC LIMIT 1;
```

**How it works:**
```
Dates:  Sep 20, 21, 22, 24, 25, 26
RowNum: 1,      2,  3,  4,  5,  6
Date-RN: Sep19, Sep19, Sep19, Sep20, Sep20, Sep20
Groups:  ────── Group 1 ──────  ──── Group 2 ────
Count:        3 days                  3 days
```

**Complexity:** O(n log n) — one pass with sort

---

## 2. Weekly Comparison (Conditional Aggregation)

**Interview question:** "How do you compare this week vs last week in one query?"

```sql
SELECT
    h.name,
    -- This week average (CASE inside AVG)
    AVG(CASE
        WHEN hl.log_date >= :this_week_start THEN
            COALESCE(hl.value_numeric, hl.value_scale::float,
                     CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END)
    END) AS this_week_avg,

    -- Last week average
    AVG(CASE
        WHEN hl.log_date >= :last_week_start AND hl.log_date < :this_week_start THEN
            COALESCE(hl.value_numeric, hl.value_scale::float,
                     CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END)
    END) AS last_week_avg,

    -- Days logged per week
    COUNT(CASE WHEN hl.log_date >= :this_week_start THEN 1 END) AS this_week_count,
    COUNT(CASE WHEN hl.log_date >= :last_week_start
                AND hl.log_date < :this_week_start THEN 1 END) AS last_week_count

FROM habits h
LEFT JOIN habit_logs hl ON h.id = hl.habit_id AND hl.log_date >= :last_week_start
WHERE h.user_id = :user_id AND h.is_archived = false
GROUP BY h.name;
```

**Key technique:** `CASE WHEN` inside `AVG()` — splits one result set into two time periods without two separate queries.

---

## 3. Monthly Trend with No Gaps (generate_series + LEFT JOIN)

**Interview question:** "How do you fill missing dates in time-series chart data?"

```sql
WITH date_range AS (
    -- Generate ALL dates in the range (even days with no logs)
    SELECT generate_series(:start::date, :end::date, '1 day')::date AS d
),
active_habits AS (
    SELECT id, name, color, habit_type
    FROM habits WHERE user_id = :uid AND is_archived = false
),
-- Every habit × every date (Cartesian product)
habit_dates AS (
    SELECT ah.id AS habit_id, ah.name, dr.d AS log_date
    FROM active_habits ah CROSS JOIN date_range dr
)
SELECT
    hd.name,
    hd.log_date,
    COALESCE(hl.value_numeric, hl.value_scale::float,
             CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END) AS value
FROM habit_dates hd
LEFT JOIN habit_logs hl ON hd.habit_id = hl.habit_id AND hd.log_date = hl.log_date
ORDER BY hd.habit_id, hd.log_date;
```

**Why generate_series:** Without it, days with no logs are missing from results. The chart would draw a straight line from Sep 20 to Sep 25, hiding the 4-day gap. With generate_series, those days show as NULL — the chart draws gaps correctly.

---

## 4. Completion Rate (GREATEST to Avoid Division by Zero)

```sql
SELECT
    h.name,
    COUNT(hl.id) AS days_logged,
    GREATEST(
        (LEAST(:end, CURRENT_DATE) - GREATEST(:start, h.created_at::date)) + 1,
        1  -- At least 1 to avoid division by zero
    ) AS total_days
FROM habits h
LEFT JOIN habit_logs hl ON h.id = hl.habit_id
    AND hl.log_date >= :start AND hl.log_date <= :end
WHERE h.user_id = :uid AND h.is_archived = false
GROUP BY h.id, h.name, h.created_at;
```

**Key technique:** `GREATEST(..., 1)` ensures we never divide by zero. A habit created today has total_days = 1, not 0.

---

## 5. Correlation Data (Self-Join for Pairs)

**Interview question:** "How do you find all pairs of habits logged on the same day?"

```sql
WITH habit_values AS (
    SELECT hl.habit_id, h.name, hl.log_date,
           COALESCE(hl.value_numeric, hl.value_scale::float,
                    CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END) AS value
    FROM habit_logs hl
    JOIN habits h ON hl.habit_id = h.id
    WHERE hl.user_id = :uid AND h.is_archived = false
)
-- Self-join: pair habits that were logged on the same day
SELECT
    a.name AS habit_a, b.name AS habit_b,
    a.value AS value_a, b.value AS value_b, a.log_date
FROM habit_values a
JOIN habit_values b ON a.log_date = b.log_date
    AND a.habit_id < b.habit_id  -- Avoid duplicates: (A,B) not (B,A) or (A,A)
ORDER BY a.habit_id, b.habit_id, a.log_date;
```

**Key technique:** `a.habit_id < b.habit_id` avoids counting (Sleep, Mood) and (Mood, Sleep) as two separate pairs. This is a standard combinatorial self-join pattern.

---

## 6. Vector Similarity Search (pgvector)

```sql
-- Find document chunks most similar to a query embedding
SELECT
    dc.chunk_text,
    dc.page_number,
    d.filename,
    1 - (dc.embedding <=> :query_embedding::vector) AS similarity
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE dc.user_id = :uid
  AND d.status = 'processed'
  AND 1 - (dc.embedding <=> :query_embedding::vector) > 0.3
ORDER BY dc.embedding <=> :query_embedding::vector
LIMIT 5;
```

**`<=>` operator:** pgvector's cosine distance. Returns 0 for identical vectors, 2 for opposite. Similarity = 1 - distance.

**IVFFlat index:** Divides vectors into clusters. Only searches nearby clusters — approximate but 10-100x faster than brute force.

---

## 7. Index Strategy Summary

| Table | Index | Query Pattern |
|-------|-------|--------------|
| users | `email` (unique) | Login lookup |
| habits | `(user_id, is_archived)` | Dashboard: active habits per user |
| habit_logs | `(user_id, log_date)` | Daily check-in page |
| habit_logs | `(habit_id, log_date)` | Streak calculation, charts |
| habit_logs | `UNIQUE(user_id, habit_id, log_date)` | Prevent duplicate logs |
| document_chunks | `IVFFlat(embedding)` | RAG similarity search |
| ai_chat_messages | `(user_id, created_at)` | Chat history (newest first) |

**Rule of thumb:** Create indexes for columns in WHERE and JOIN ON clauses of your most frequent queries. Every index speeds reads but slows writes.
