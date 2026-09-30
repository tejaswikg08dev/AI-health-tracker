# Phase 4 — Part 03e: Structured Logging (shared/logging.py)

| Field | Value |
|-------|-------|
| **Part** | 03e |
| **File** | `backend/app/shared/logging.py` |
| **Next** | [Part 03f — error_handler.py](./phase4-part03f-error-handler.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~12 minutes |
| **Lines** | ~70 lines |

---

## What is Structured Logging? Read This First

```
UNSTRUCTURED (print statements):
  "User 123 created habit Water Intake at 2026-09-26 10:00:00"
  → How do you search for all actions by user 123? Regex on strings. Painful.

STRUCTURED (JSON):
  {"event": "habit_created", "user_id": "123", "habit_name": "Water Intake", "timestamp": "2026-09-26T10:00:00Z"}
  → Elasticsearch query: user_id == "123" → instant results
```

Structured logs are **machine-readable** (JSON), not just human-readable. This enables:
- Searching in Elasticsearch/CloudWatch
- Dashboards in Kibana/Grafana
- Alerting on error patterns
- Debugging production issues at 3 AM

---

## Source Code

> 📁 **File:** `backend/app/shared/logging.py`
> Type the full code from the source file

Key decisions:
- **Development:** Colored console output (human-readable)
- **Production:** JSON output (machine-parseable for ELK/CloudWatch)
- **Both:** Include log level, timestamp, filename, line number

---

## 🎤 Interview Q&A

### Q: "How do you handle logging in your application?"

> "Structlog for structured JSON logging. In development, logs are colored console output for readability. In production, they're JSON — each log entry is a key-value dictionary that Elasticsearch or CloudWatch can index and search. Every request gets a unique `request_id` that flows through all log entries, so I can trace a single request across the entire system. I log at different levels: `info` for normal operations, `warning` for expected errors (rate limiting, validation), `error` for unexpected failures with full tracebacks."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03d](./phase4-part03d-date-utils.md) | | [Part 03f — error_handler.py](./phase4-part03f-error-handler.md) |
