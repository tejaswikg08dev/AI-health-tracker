# 🤖 Phase 4 Part 08c: AI LLM — Prompt Templates & Token Tracker

> **"Prompt engineering is 80% of AI application quality. The same model with a bad prompt gives generic answers. With a great prompt — persona, rules, context injection, output format — it gives expert-level responses. And token tracking ensures you don't wake up to a surprise $500 bill."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 08c (AI LLM Prompts & Token Tracking) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.1 — AI Chat + LLM Integration |
| **Previous** | [phase4-part08b-ai-llm-providers.md](./phase4-part08b-ai-llm-providers.md) |
| **Next** | [phase4-part09-ai-rag-overview.md](./phase4-part09-ai-rag-overview.md) |
| **Files in This Doc** | 2 files (prompt_templates.py, token_tracker.py) |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (Jinja2 templates, prompt engineering principles, Redis counters) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [Concept: Prompt Engineering](#prompt-engineering)
3. [File 1: prompt_templates.py — Full Source Code](#prompts)
4. [File 2: token_tracker.py — Full Source Code](#tokens)
5. [Token Economics — What AI Actually Costs](#economics)
6. [Design Decisions](#design-decisions)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Two files that complete the LLM layer:

| File | What It Does | Why It Matters |
|------|-------------|---------------|
| `prompt_templates.py` | Stores all AI prompts as Jinja2 templates | Quality: a good prompt = a good AI response |
| `token_tracker.py` | Tracks token usage per user per day in Redis | Cost: prevents surprise bills, enables rate limiting |

---

<a name="prompt-engineering"></a>
## 2. Concept: Prompt Engineering

### What Is a Prompt?

A **prompt** is the full text sent to the LLM — system instructions + context + the user's question. The LLM generates its response based ONLY on what's in the prompt.

```
BAD PROMPT (generic):
  System: "You are an AI assistant."
  User: "How's my sleep?"
  → AI: "Sleep is important for health. Adults need 7-9 hours."
  ← Useless. Generic knowledge. No data.

GOOD PROMPT (specific):
  System: "You are a friendly health coach for Shreya.
           She tracks 6 habits. Be specific with numbers.
           Reference actual data. Give actionable advice."
  Context: "This week's data: Sleep avg 6.8h (down 5.6% from 7.2h).
           Sleep↔Mood correlation: r=0.72 (strong positive).
           Exercise: 0 days this week (was 4 last week)."
  User: "How's my sleep?"
  → AI: "Your sleep averaged 6.8 hours this week, down from 7.2 last
         week. Notably, you didn't exercise at all this week — and your
         data shows a strong link between exercise and sleep (r=0.72).
         Try a 20-minute walk tomorrow to kickstart both."
  ← Specific, data-driven, actionable.
```

### Prompt Structure (System → Context → User)

```
┌─────────────────────────────────────────────────────────────────┐
│  SYSTEM MESSAGE (who the AI is + rules)                          │
│  "You are a friendly health coach for Shreya.                    │
│   Be specific with numbers. Give actionable advice."             │
├─────────────────────────────────────────────────────────────────┤
│  CONTEXT (injected data — from DB/analytics/RAG)                 │
│  "Recent data: Sleep 6.8h avg, Water 7.4 avg, Mood 5.7 avg.    │
│   Streaks: Water 15 days. Correlations: Sleep↔Mood r=0.72."     │
├─────────────────────────────────────────────────────────────────┤
│  USER MESSAGE (what the user asked)                              │
│  "How's my sleep?"                                               │
├─────────────────────────────────────────────────────────────────┤
│  ASSISTANT RESPONSE (what the LLM generates)                     │
│  "Your sleep averaged 6.8 hours this week..."                    │
└─────────────────────────────────────────────────────────────────┘
```

### What Is Jinja2?

**Jinja2** is a template engine — it lets you inject variables into text:

```python
from jinja2 import Template

template = Template("Hello {{ name }}, you track {{ count }} habits.")
result = template.render(name="Shreya", count=6)
# → "Hello Shreya, you track 6 habits."
```

We use Jinja2 for prompts because:
- Variables: `{{ user_name }}`, `{{ habit_count }}`
- Loops: `{% for habit in habits %}...{% endfor %}`
- Conditionals: `{% if change_pct %}({{ change_pct }}% change){% endif %}`
- Readable: templates look like the final output with placeholders

---

<a name="prompts"></a>
## 3. File 1: `prompt_templates.py` — Full Source Code

### Type This Code: `backend/app/modules/ai/llm/prompt_templates.py`

```python
# ============================================================================
# LLM — Prompt Templates
# ============================================================================
# WHAT THIS FILE DOES:
#   Stores all prompt templates used by the AI features.
#   Templates use Jinja2 syntax — variables are injected at runtime.
#
# WHY TEMPLATES (not hardcoded strings):
#   1. Readable — templates are easier to read than f-strings with 20 variables
#   2. Maintainable — change the prompt without touching Python code
#   3. Testable — test templates independently from the LLM call
#   4. Versionable — git diff shows exactly what changed in a prompt
#
# PROMPT ENGINEERING TIPS:
#   - Be specific about the role ("You are a health coach")
#   - Give constraints ("Only reference data provided below")
#   - Include examples of desired output format
#   - Use structured data (tables, lists) for context injection
#   - End with a clear instruction ("Answer the user's question")
# ============================================================================

from jinja2 import Template


# ── System Prompts ──

HEALTH_COACH_SYSTEM = Template("""You are a friendly, knowledgeable personal health coach.
You help users understand their health habits and make better choices.

RULES:
1. Be supportive and encouraging, never judgmental.
2. Reference ACTUAL data from the user's habit logs when available.
3. Use specific numbers: "You averaged 6.8 hours" not "You slept less."
4. If you don't have enough data, say so honestly.
5. Keep responses concise: 3-5 sentences for simple questions, more for analysis.
6. Suggest actionable improvements, not vague advice.
7. If asked about medical conditions, recommend consulting a doctor.

USER INFO:
- Name: {{ user_name }}
- Timezone: {{ timezone }}
- Tracking {{ habit_count }} habits
""")


# ── Context Templates ──

USER_DATA_CONTEXT = Template("""
RECENT HABIT DATA (last {{ days }} days):
{% for date, logs in daily_logs.items() %}
{{ date }}:
{% for log in logs %}  - {{ log.habit_name }}: {{ log.value }} {{ log.unit }}
{% endfor %}{% endfor %}

CURRENT STREAKS:
{% for streak in streaks %}
- {{ streak.habit_name }}: {{ streak.current_streak }} days (best: {{ streak.longest_streak }})
{% endfor %}

WEEKLY COMPARISON (this week vs last week):
{% for habit in weekly %}
- {{ habit.habit_name }}: {{ habit.this_week_avg }} → {{ habit.last_week_avg }}{% if habit.change_pct %} ({{ habit.change_pct }}% change){% endif %}
{% endfor %}
""")


RAG_CONTEXT = Template("""
RELEVANT INFORMATION FROM YOUR DOCUMENTS:
{% for chunk in chunks %}
[Source: {{ chunk.filename }}, Page {{ chunk.page_number }}]
{{ chunk.text }}
---
{% endfor %}

Use the above information to help answer the user's question.
Always cite sources when referencing document content.
""")


# ── Agent Prompts ──

AGENT_SYSTEM = Template("""You are a health coach AI agent with access to tools.

You can use the following tools to gather information before responding:
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
{% endfor %}

INSTRUCTIONS:
1. Think about what information you need to answer the user's question.
2. Use tools to fetch real data — never make up numbers.
3. You can call multiple tools if needed.
4. After gathering data, provide a comprehensive answer.
5. Be specific and reference the actual numbers from the tool results.

USER: {{ user_name }} (tracking {{ habit_count }} habits)
""")


# ── Workflow Prompts ──

WEEKLY_REPORT_ANALYSIS = Template("""Analyze this week's health data and provide insights.

DATA SUMMARY:
{{ data_summary }}

INSTRUCTIONS:
1. Identify the top 3 improvements this week.
2. Identify any concerning trends or declines.
3. Note any correlations you see (e.g., sleep affecting mood).
4. Provide 2-3 specific, actionable recommendations for next week.
5. Keep the tone encouraging and supportive.
6. Reference specific numbers from the data.

Format your response as a structured report with sections:
## Highlights
## Areas to Watch
## Recommendations
""")


WEEKLY_REPORT_WRITER = Template("""Write a personalized weekly health report for {{ user_name }}.

DATA:
{{ data_summary }}

ANALYSIS:
{{ analysis }}

Write a friendly, personalized weekly report. Include:
- A brief greeting mentioning their best achievement
- Key stats in an easy-to-scan format
- The analysis insights in natural language
- A motivating closing message

Keep it under 500 words. Use markdown formatting.
""")


# ── Insight Generation ──

INSIGHT_PROMPT = Template("""Based on this user's health data, generate a brief insight.

DATA:
{{ data_context }}

Generate ONE specific, actionable insight. Examples:
- "Your mood is 23% higher on days you exercise. Try scheduling workouts on your low-mood days."
- "You've been sleeping 45 minutes less on weekdays vs weekends. A consistent sleep schedule could help."

Be specific with numbers. Keep it to 2-3 sentences.
""")
```

### Template-by-Template Explanation

**`HEALTH_COACH_SYSTEM` — The AI's Persona**

This is the MOST important prompt. It defines WHO the AI is, WHAT rules it follows, and WHAT context it has. Every chat session starts with this as the system message.

Key elements:
- **Role:** "You are a friendly, knowledgeable personal health coach" — sets the persona
- **Rules:** 7 numbered rules — the AI follows these strictly. Rule 3 ("Use specific numbers") is crucial for data-driven responses
- **User info:** Name, timezone, habit count — personalization without exposing sensitive data
- **`{{ user_name }}`** — Jinja2 variable, replaced at runtime with the actual user's name

**`USER_DATA_CONTEXT` — Injected Data**

This template builds the data context from real database values:

```python
context = USER_DATA_CONTEXT.render(
    days=7,
    daily_logs={"Sep 25": [{"habit_name": "Water", "value": 7, "unit": "glasses"}], ...},
    streaks=[{"habit_name": "Water", "current_streak": 15, "longest_streak": 30}],
    weekly=[{"habit_name": "Sleep", "this_week_avg": 6.8, "last_week_avg": 7.2, "change_pct": -5.6}],
)
```

Output:
```
RECENT HABIT DATA (last 7 days):
Sep 25:
  - Water: 7 glasses
  - Sleep: 7.5 hours

CURRENT STREAKS:
- Water: 15 days (best: 30)

WEEKLY COMPARISON:
- Sleep: 6.8 → 7.2 (-5.6% change)
```

**`RAG_CONTEXT` — Document Chunks**

Injects retrieved document chunks with source citations:
```
RELEVANT INFORMATION FROM YOUR DOCUMENTS:
[Source: Sleep Guide.pdf, Page 3]
Magnesium-rich foods like almonds help sleep quality...
---
[Source: Sleep Guide.pdf, Page 7]
Avoid caffeine after 2 PM as it blocks adenosine...
---
```

The "Always cite sources" instruction ensures the AI says "According to your Sleep Guide..." not just the raw content.

**`AGENT_SYSTEM` — Tool Descriptions for the Agent**

Lists available tools so the LLM knows what it can call:
```
You can use the following tools:
- query_logs: Get habit log data for a date range
- get_analytics: Get streaks, weekly summary, or trends
- correlate: Find correlations between habits
```

**`WEEKLY_REPORT_ANALYSIS` + `WEEKLY_REPORT_WRITER` — Two-Step Workflow**

The weekly report uses a two-step process:
1. **Analysis step:** LLM identifies patterns and insights (structured output)
2. **Writing step:** LLM formats the analysis as a friendly report (natural language)

Why two steps? One prompt that does both produces worse results. Separating analysis from writing (like asking an analyst and a writer to collaborate) produces higher quality.

---

<a name="tokens"></a>
## 4. File 2: `token_tracker.py` — Full Source Code

### Type This Code: `backend/app/modules/ai/llm/token_tracker.py`

```python
# ============================================================================
# LLM — Token Usage Tracker
# ============================================================================
# WHAT THIS FILE DOES:
#   Tracks how many tokens each user consumes per day.
#   Used for: cost monitoring, rate limiting AI usage, analytics.
#
# WHY TRACK TOKENS:
#   Even with free providers (Ollama, Groq), tracking tokens teaches you
#   the production skill of cost management. In production with OpenAI:
#   - GPT-4: $0.03 per 1K input tokens
#   - A user sending 100 messages/day = $3-10/day = $100-300/month
#   - Without tracking, one abusive user could cost you thousands
#
# STORAGE: Redis (fast writes, auto-expiry for daily counters)
# ============================================================================

from datetime import date

import redis.asyncio as redis

from app.shared.date_utils import today_utc
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Daily token limits per user (adjustable)
DAILY_TOKEN_LIMIT = 50000  # ~50 conversations per day with context


class TokenTracker:
    """
    Tracks token usage per user per day in Redis.

    Key format: "tokens:{user_id}:{date}"
    Value: total tokens used today
    TTL: 48 hours (auto-cleanup, keeps yesterday for reference)
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def track_usage(
        self,
        user_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> int:
        """
        Record token usage for a request.

        Returns the updated total for today.
        """
        today = str(today_utc())
        key = f"tokens:{user_id}:{today}"
        total = input_tokens + output_tokens

        try:
            new_total = await self.redis.incrby(key, total)
            # Set expiry if this is the first request today
            if new_total == total:
                await self.redis.expire(key, 172800)  # 48 hours
            return new_total
        except Exception:
            logger.warning("token_tracking_error", user_id=user_id)
            return 0

    async def get_usage_today(self, user_id: str) -> int:
        """Get total tokens used today by this user."""
        today = str(today_utc())
        key = f"tokens:{user_id}:{today}"

        try:
            usage = await self.redis.get(key)
            return int(usage) if usage else 0
        except Exception:
            return 0

    async def check_limit(self, user_id: str) -> tuple[bool, int]:
        """
        Check if user has exceeded their daily token limit.

        Returns:
            (is_allowed, tokens_remaining)
        """
        usage = await self.get_usage_today(user_id)
        remaining = max(0, DAILY_TOKEN_LIMIT - usage)
        return remaining > 0, remaining
```

### Key Concepts in token_tracker.py

**Redis INCRBY — Atomic Counter**
```python
new_total = await self.redis.incrby(key, total)
```
- `INCRBY` atomically increments a Redis key by the given amount
- If the key doesn't exist, it's created with the increment value
- Atomic = no race conditions. 100 concurrent requests all update the same counter correctly
- Returns the new total after incrementing

**Auto-Expiry Pattern**
```python
if new_total == total:
    await self.redis.expire(key, 172800)  # 48 hours
```
- `new_total == total` means this is the FIRST increment (the counter was just created)
- Set 48-hour expiry so old daily counters auto-delete
- 48 hours (not 24) — keeps yesterday's data for comparison
- Same pattern as rate limiter and token blacklist

**Daily Key Format**
```
tokens:uuid-001:2026-09-26 → 12450 (tokens used today)
tokens:uuid-001:2026-09-25 → 8200  (yesterday, still available for 24h)
tokens:uuid-001:2026-09-24 → (auto-deleted, TTL expired)
```

**Limit Check**
```python
async def check_limit(self, user_id: str) -> tuple[bool, int]:
    usage = await self.get_usage_today(user_id)
    remaining = max(0, DAILY_TOKEN_LIMIT - usage)
    return remaining > 0, remaining
```
- Called before every AI chat request
- Returns a tuple: `(True, 37550)` = allowed, 37550 tokens remaining
- Returns `(False, 0)` = limit reached, blocked
- The service shows a friendly message: "You've used your daily AI allowance. Try again tomorrow."

---

<a name="economics"></a>
## 5. Token Economics — What AI Actually Costs

### What Is a Token?

A **token** is roughly ¾ of a word. "Hello, how are you today?" = 7 tokens.

```
"Magnesium helps sleep" = 4 tokens
"Your sleep averaged 6.8 hours this week" = 9 tokens
A typical AI chat message = 200-500 tokens (input + output)
A full agent conversation (3 tool calls) = 2000-5000 tokens
```

### Cost Per Provider

| Provider | Input Cost | Output Cost | Typical Chat Cost |
|----------|-----------|------------|------------------|
| **Ollama** | $0 | $0 | **$0** (local) |
| **Groq** | $0 | $0 | **$0** (free tier) |
| **OpenAI GPT-4o** | $0.005/1K | $0.015/1K | **~$0.01-0.05** per chat |
| **OpenAI GPT-3.5** | $0.0005/1K | $0.0015/1K | **~$0.001-0.005** per chat |

### Monthly Cost Estimation

| Usage Level | Messages/Day | Tokens/Day | OpenAI GPT-4o/Month |
|-------------|-------------|------------|---------------------|
| Light (1 user) | 10 | 10,000 | ~$5 |
| Moderate (1 user) | 50 | 50,000 | ~$25 |
| Heavy (1 user) | 100 | 100,000 | ~$50 |
| 100 users | 1,000 | 1,000,000 | ~$500 |

**This is why the token tracker matters.** One user sending 100 messages/day with GPT-4 costs $50/month. Without limits, a bot could run up thousands.

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision: Jinja2 Templates vs f-strings

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Prompt Storage Strategy                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Jinja2 templates in a dedicated file                       │
│                                                                     │
│  WHY:                                                               │
│  • Loops and conditionals ({% for %}, {% if %}) — f-strings can't  │
│  • Readable: template looks like the final output with placeholders │
│  • Versionable: git diff shows exactly what changed in a prompt     │
│  • Testable: render a template and assert the output                │
│  • Separation: prompt changes don't require touching Python logic   │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. f-strings with string concatenation                             │
│     ❌ Unreadable with 20+ variables and loops                     │
│  2. External YAML/JSON files                                        │
│     ⚠️ Adds file I/O complexity, harder to reference in code       │
│  3. Prompt management platforms (Langfuse, PromptLayer)             │
│     ⚠️ External dependency, overkill for a learning project        │
│                                                                     │
│  INTERVIEW TIP: "We store prompts as Jinja2 templates in a         │
│  dedicated file. Templates support loops, conditionals, and are     │
│  version-controlled. Changing a prompt is a one-line git diff —     │
│  no Python logic changes needed."                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision: Redis for Token Tracking

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Token Usage Storage                               │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Redis with daily counters and auto-expiry                  │
│                                                                     │
│  WHY:                                                               │
│  • Fast writes — INCRBY is O(1), handles concurrent requests        │
│  • Auto-cleanup — TTL expires old daily counters automatically      │
│  • No schema — don't need a database table for transient counters   │
│  • Already have Redis — no new infrastructure                       │
│                                                                     │
│  ALTERNATIVES:                                                      │
│  1. PostgreSQL table (token_usage)                                  │
│     ❌ Write overhead on every AI request, migration needed         │
│  2. In-memory counter (Python dict)                                 │
│     ❌ Lost on restart, doesn't work with multiple servers          │
│                                                                     │
│  INTERVIEW TIP: "We use Redis INCRBY for atomic token counting     │
│  with 48-hour TTL for auto-cleanup. It's O(1) writes, handles      │
│  concurrency, and requires no schema migration."                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Prompt Engineering** | Crafting system prompts that produce quality AI responses | All templates |
| 2 | **System → Context → User** | Three-part prompt structure (persona, data, question) | HEALTH_COACH_SYSTEM |
| 3 | **Jinja2 `Template()`** | Template engine with `{{ vars }}`, `{% loops %}`, `{% if %}` | All templates |
| 4 | **`template.render()`** | Inject variables into a template | Called by service |
| 5 | **Two-step prompting** | Separate analysis from writing for better quality | WEEKLY_REPORT_* |
| 6 | **Source citation** | "Always cite sources" instruction in RAG context | RAG_CONTEXT |
| 7 | **Tool descriptions in prompt** | LLM sees tool list → decides which to call | AGENT_SYSTEM |
| 8 | **Tokens** | ~¾ word. Input + output = total cost | Token economics |
| 9 | **Redis INCRBY** | Atomic counter increment — safe for concurrency | track_usage() |
| 10 | **Daily token limit** | 50,000 tokens/day/user — prevents abuse | check_limit() |
| 11 | **Auto-expiry (TTL)** | Old daily counters self-delete after 48 hours | expire() call |
| 12 | **`tuple[bool, int]` return** | (is_allowed, remaining) — clean API | check_limit() |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: How do you structure your AI prompts?
**A:** "Three layers: system message (persona + rules), context (injected data from DB/RAG), and user message. The system prompt defines the AI's persona ('friendly health coach'), behavioral rules ('use specific numbers, not vague statements'), and user context (name, timezone). Data context is generated from real database queries — habit logs, streaks, weekly summaries — injected via Jinja2 templates. The user's question is the final message. This structure ensures the AI always responds with personalized, data-driven answers."

### Q2: Why Jinja2 instead of f-strings for prompts?
**A:** "Jinja2 supports loops (`{% for habit in habits %}`) and conditionals (`{% if change_pct %}`) that f-strings can't handle. Our data context template iterates over daily logs, streaks, and weekly comparisons — this would be unreadable as an f-string. Templates are also version-controlled: a prompt change shows as a clean git diff without touching Python logic. And they're testable independently — render the template with test data and assert the output."

### Q3: How does the two-step weekly report workflow improve quality?
**A:** "One prompt that both analyzes data AND writes a report produces mediocre results — the LLM tries to do both at once. By separating into two steps: (1) analyze data → identify patterns and insights (structured), then (2) write a friendly report from the analysis, each step has a focused task. It's like asking an analyst to find insights, then asking a writer to turn those insights into a readable report. The quality of each step is higher because the scope is narrower."

### Q4: How does token tracking work and why is it important?
**A:** "Each AI request returns input_tokens and output_tokens in the LLMResponse. After every request, the service calls `token_tracker.track_usage(user_id, input, output)` which does a Redis INCRBY on the key `tokens:{user_id}:{date}`. Before each AI request, `check_limit()` verifies the user hasn't exceeded 50,000 daily tokens. With OpenAI GPT-4 at $0.005/1K input tokens, an unlimited user could run up hundreds of dollars. Token tracking is how companies control AI costs in production."

### Q5: What makes a good AI prompt vs a bad one?
**A:** "A bad prompt: 'You are an AI. Answer the question.' — generic, no rules, no data. A good prompt: defines a specific persona ('health coach'), sets behavioral rules ('use specific numbers, never make up data, suggest actionable improvements'), injects real user data (habit logs, streaks, correlations), and structures the expected output format. The prompt IS the product — same model, bad prompt = useless; same model, great prompt = expert-level responses."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 08b: AI LLM Providers + Factory](./phase4-part08b-ai-llm-providers.md) |
| ➡️ Next | [Phase 4 Part 09: AI RAG Pipeline Overview](./phase4-part09-ai-rag-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### LLM Layer — All Sub-Parts Complete ✅

| Sub-Part | Status | Document |
|----------|--------|----------|
| 08a | ✅ Done | LLM Base Client (Strategy pattern interface) |
| 08b | ✅ Done | LLM Providers + Factory |
| **08c** | ✅ **Done** | LLM Prompts & Tokens |

---

**🎉 The LLM layer is COMPLETE.**

*8 files: abstract interface, 3 providers, factory, prompt templates, and token tracking. The AI can talk to any LLM provider, stream responses, embed text for RAG, and track costs. Next: the RAG pipeline — giving the AI access to your documents.*
