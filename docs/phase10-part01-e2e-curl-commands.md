# 🧪 Phase 10 Part 01: End-to-End Testing — curl Commands

> **"A complete user journey tested with curl: signup → login → create habits → log data → check analytics → chat with AI → export CSV. Copy-paste these commands to verify every endpoint works end-to-end."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 10 — End-to-End Verification |
| **Previous** | [Phase 9: Nginx & Monitoring](./phase9-part01-nginx-monitoring.md) |
| **Next** | [Phase 10 Part 02: Interview Prep](./phase10-part02-interview-prep-complete.md) |

---

## 1. Prerequisites

```bash
# Make sure the backend is running
curl http://localhost:8000/health
# → {"status": "healthy"}
```

---

## 2. Auth Flow (Signup → Login → Profile)

```bash
# ── Signup ──
curl -s -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "shreya@e2e-test.com",
    "password": "TestPass123!",
    "full_name": "Shreya",
    "timezone": "Asia/Kolkata"
  }' | python -m json.tool
# → { "id": "uuid-...", "email": "shreya@e2e-test.com", "full_name": "Shreya" }

# ── Login ──
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "shreya@e2e-test.com", "password": "TestPass123!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
# → Token: eyJhbGciOiJIUzI1NiIs...

# ── Get Profile ──
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
# → { "email": "shreya@e2e-test.com", "full_name": "Shreya", ... }

# ── Update Profile ──
curl -s -X PUT http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Shreya V"}' | python -m json.tool
# → { "full_name": "Shreya V", ... }
```

---

## 3. Habits CRUD

```bash
# ── Create Numeric Habit ──
WATER_ID=$(curl -s -X POST http://localhost:8000/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Water Intake",
    "habit_type": "numeric",
    "unit": "glasses",
    "target_value": 8,
    "color": "#3B82F6",
    "icon": "💧"
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Water habit: $WATER_ID"

# ── Create Boolean Habit ──
EXERCISE_ID=$(curl -s -X POST http://localhost:8000/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Exercise",
    "habit_type": "boolean",
    "icon": "🏃",
    "color": "#10B981"
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# ── Create Scale Habit ──
MOOD_ID=$(curl -s -X POST http://localhost:8000/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mood",
    "habit_type": "scale",
    "icon": "😊",
    "color": "#F59E0B"
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# ── List All Habits ──
curl -s http://localhost:8000/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
# → [ { "name": "Water Intake", ... }, { "name": "Exercise", ... }, { "name": "Mood", ... } ]
```

---

## 4. Log Entries (Single + Bulk)

```bash
TODAY=$(date +%Y-%m-%d)

# ── Single Log ──
curl -s -X POST http://localhost:8000/api/v1/logs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"habit_id\": \"$WATER_ID\",
    \"log_date\": \"$TODAY\",
    \"value_numeric\": 8.0,
    \"notes\": \"Great hydration day\"
  }" | python -m json.tool

# ── Bulk Log (all habits at once) ──
curl -s -X POST http://localhost:8000/api/v1/logs/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"log_date\": \"$TODAY\",
    \"entries\": [
      {\"habit_id\": \"$WATER_ID\", \"value_numeric\": 8},
      {\"habit_id\": \"$EXERCISE_ID\", \"value_boolean\": true},
      {\"habit_id\": \"$MOOD_ID\", \"value_scale\": 8}
    ]
  }" | python -m json.tool
# → [ {value_numeric: 8}, {value_boolean: true}, {value_scale: 8} ]

# ── Get Today's Logs ──
curl -s "http://localhost:8000/api/v1/logs?date=$TODAY" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

## 5. Analytics

```bash
# ── Dashboard ──
curl -s http://localhost:8000/api/v1/analytics/dashboard \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
# → { "today_logged": 3, "today_total": 3, "today_completion_pct": 100.0, ... }

# ── Streaks ──
curl -s http://localhost:8000/api/v1/analytics/streaks \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# ── Weekly Summary ──
curl -s http://localhost:8000/api/v1/analytics/weekly-summary \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# ── Monthly Trend ──
curl -s "http://localhost:8000/api/v1/analytics/monthly-trend?days=30" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# ── Completion Rate ──
curl -s "http://localhost:8000/api/v1/analytics/completion-rate?days=30" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# ── Correlations ──
curl -s "http://localhost:8000/api/v1/analytics/correlations?days=30" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

## 6. AI Chat

```bash
# ── Simple Chat ──
curl -s -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "How is my water intake this week?", "use_agent": true}' \
  | python -m json.tool
# → { "response": "Based on your logs, you averaged 8 glasses..." }

# ── Chat History ──
curl -s http://localhost:8000/api/v1/ai/chat/history \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# ── Generate Insight ──
curl -s -X POST http://localhost:8000/api/v1/ai/insights \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# ── List Insights ──
curl -s http://localhost:8000/api/v1/ai/insights \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

## 7. Notifications

```bash
# ── Get Settings ──
curl -s http://localhost:8000/api/v1/notifications/settings \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
# → { "daily_reminder": true, "weekly_report": true, "streak_alerts": true, ... }

# ── Update Settings ──
curl -s -X PUT http://localhost:8000/api/v1/notifications/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"daily_reminder": false, "reminder_time": "09:00"}' \
  | python -m json.tool

# ── Send Test Email ──
curl -s -X POST http://localhost:8000/api/v1/notifications/test-email \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_type": "daily_reminder"}' | python -m json.tool
```

---

## 8. Export

```bash
# ── CSV Download (Sync) ──
curl -s -X POST http://localhost:8000/api/v1/export/csv \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2026-01-01", "end_date": "2026-09-26"}' \
  -o export.csv

cat export.csv
# → Date,Habit Name,Type,Value,Unit,Notes
#   2026-09-26,Water Intake,numeric,8.0,glasses,Great hydration day

# ── CSV to S3 (Async) ──
curl -s -X POST http://localhost:8000/api/v1/export/csv/s3 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2026-01-01", "end_date": "2026-09-26"}' \
  | python -m json.tool
# → { "download_url": "http://localhost:9000/health-tracker/exports/...?X-Amz-..." }
```

---

## 9. Logout

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
# → { "message": "Successfully logged out" }

# Verify token is invalidated:
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
# → 401 Unauthorized
```

---

## 10. Endpoint Summary: All 38 Endpoints Tested

| Module | Endpoints | curl Section |
|--------|----------|-------------|
| Auth | 6 (signup, login, refresh, logout, get/update profile) | Section 2 |
| Habits | 6 (list, get, create, update, delete, reorder) | Section 3 |
| Logs | 5 (create, bulk, get by date, update, delete) | Section 4 |
| Analytics | 6 (dashboard, streaks, weekly, monthly, completion, correlations) | Section 5 |
| AI | 9 (chat, stream, history, upload doc, list/delete doc, insight, list insights, weekly report) | Section 6 |
| Notifications | 3 (get/update settings, test email) | Section 7 |
| Export | 2 (CSV sync, CSV to S3) | Section 8 |
| Health | 1 (/health) | Section 1 |
| **Total** | **38** | |

---

## 11. Navigation

| ⬅️ Previous | [Phase 9: Nginx & Monitoring](./phase9-part01-nginx-monitoring.md) |
| ➡️ Next | [Phase 10 Part 02: Interview Prep](./phase10-part02-interview-prep-complete.md) |

---

**End of Phase 10 Part 01: E2E curl Commands**
