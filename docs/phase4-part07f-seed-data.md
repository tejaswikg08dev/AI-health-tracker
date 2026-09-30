# 🌱 Phase 4 Part 07f: Seed Data Script

> **"Seed data populates the database with realistic test data so analytics, AI, and charts have something to work with. Without it, every dashboard is empty."**

---

## What `scripts/seed_data.py` Does

1. Creates a test user (shreya@test.com)
2. Creates 6 habits (Water, Sleep, Exercise, Mood, Meditation, Steps)
3. Creates 30 days of realistic log data (with natural variation)
4. Result: dashboard, streaks, correlations all populated

```bash
docker-compose exec backend python scripts/seed_data.py
```

After seeding: login → dashboard shows "15-day water streak", analytics shows charts with 30 days of data, AI can answer "How was my sleep this week?" with real numbers.

---

| ⬅️ Previous | [Part 07e: Analytics Flows](./phase4-part07e-analytics-connections-and-flows.md) |
| ➡️ Next | [Part 08: AI LLM Overview](./phase4-part08-ai-llm-overview.md) |
