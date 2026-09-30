# 🧠 Phase 4 Part 10b: AI Agent — Memory

> **"Without memory, every message is a fresh start — the AI forgets you asked about sleep 3 messages ago. Short-term memory tracks the conversation. Long-term memory remembers you're vegetarian across sessions. Together, they make the AI feel like it knows you."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 10b (Agent Memory) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.3 — AI Agent + Tools |
| **Previous** | [phase4-part10a-ai-agent-tools.md](./phase4-part10a-ai-agent-tools.md) |
| **Next** | [phase4-part10c-ai-agent-react-loop.md](./phase4-part10c-ai-agent-react-loop.md) |
| **Files in This Doc** | 2 files (short_term.py, long_term.py) |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (sliding window buffer, Redis hashes, prompt injection) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: short_term.py — Conversation Buffer](#short-term)
3. [File 2: long_term.py — Persistent Insights](#long-term)
4. [How Memory Integrates with the Agent](#integration)
5. [Design Decisions](#design-decisions)
6. [What You Learned](#what-you-learned)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Two memory systems that solve different problems:

| Memory | Lifetime | Storage | Capacity | Purpose |
|--------|----------|---------|----------|---------|
| **Short-Term** | One conversation | In-memory (Python list) | Last 20 messages | "What did we just talk about?" |
| **Long-Term** | Forever | Redis hash (+ DB backup) | 20 key insights | "What do I know about this user?" |

### Why Two Memory Types?

```
WITHOUT SHORT-TERM MEMORY:
  User: "How's my sleep?"
  Agent: "You averaged 6.8 hours this week."
  User: "What about last week?"
  Agent: "What about last week for what? I don't know what you're asking about."
  ← Forgot the topic was sleep!

WITH SHORT-TERM MEMORY:
  User: "How's my sleep?"
  Agent: "You averaged 6.8 hours this week."
  User: "What about last week?"
  Agent: "Last week you averaged 7.2 hours — so you're sleeping 5.6% less."
  ← Remembers the conversation context!

WITHOUT LONG-TERM MEMORY:
  Session 1: "I'm vegetarian"
  Session 2: "What should I eat for iron?"
  Agent: "Try red meat and liver."
  ← Forgot they're vegetarian!

WITH LONG-TERM MEMORY:
  Session 2: "What should I eat for iron?"
  Agent: "Since you're vegetarian, try spinach, lentils, and fortified cereals."
  ← Remembered across sessions!
```

---

<a name="short-term"></a>
## 2. File 1: `short_term.py` — Conversation Buffer

### Type This Code: `backend/app/modules/ai/agents/memory/short_term.py`

```python
# ============================================================================
# Agent Memory — Short-Term (Conversation Buffer)
# ============================================================================
# WHAT THIS FILE DOES:
#   Maintains the current conversation history (last N messages).
#   This is the agent's "working memory" — what was said in THIS conversation.
#
# WHY SHORT-TERM MEMORY:
#   User: "How much water did I drink this week?"
#   Agent: "You averaged 7 glasses per day this week."
#   User: "How about last week?"  ← agent needs to remember the topic is water!
#
# HOW IT WORKS:
#   - Stores the last N messages (default: 20)
#   - Older messages are dropped (sliding window)
#   - Messages are stored as LLMMessage objects (role + content)
#   - In-memory only — cleared when the session ends
#
# TOKEN BUDGET:
#   Conversation history uses tokens from the context window.
#   20 messages × ~100 tokens each = ~2000 tokens for history.
#   We cap it to leave room for: system prompt + tool results + response.
# ============================================================================

from app.modules.ai.llm.base_client import LLMMessage


class ShortTermMemory:
    """
    Sliding window conversation buffer.

    Keeps the last `max_messages` messages in memory.
    When the buffer is full, the oldest message is dropped.

    Usage:
        memory = ShortTermMemory(max_messages=20)
        memory.add_user_message("How much water did I drink?")
        memory.add_assistant_message("You averaged 7 glasses.")
        messages = memory.get_messages()  # → list of LLMMessage
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: list[LLMMessage] = []

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self._add(LLMMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant response to the conversation."""
        self._add(LLMMessage(role="assistant", content=content))

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """
        Add a tool execution result to the conversation.

        Formatted so the LLM knows this is data from a tool, not a human.
        """
        self._add(LLMMessage(
            role="tool",
            content=f"[Tool: {tool_name}]\n{result}",
        ))

    def get_messages(self) -> list[LLMMessage]:
        """Get the current conversation history."""
        return list(self._messages)

    def get_message_count(self) -> int:
        """Get the number of messages in the buffer."""
        return len(self._messages)

    def clear(self) -> None:
        """Clear all messages (start fresh conversation)."""
        self._messages.clear()

    def _add(self, message: LLMMessage) -> None:
        """Add a message, dropping the oldest if at capacity."""
        self._messages.append(message)
        # Sliding window — drop oldest messages when buffer is full
        while len(self._messages) > self.max_messages:
            self._messages.pop(0)
```

### Key Concepts

**Sliding Window Buffer**
```python
while len(self._messages) > self.max_messages:
    self._messages.pop(0)  # Remove the oldest message
```
- `pop(0)` removes the FIRST element (oldest message)
- After adding a 21st message, the 1st message is dropped
- The LLM always sees the most recent 20 messages
- This keeps the token count predictable: 20 × ~100 tokens = ~2000 tokens

**Three Message Types**
```python
add_user_message("How's my sleep?")     → LLMMessage(role="user", content="...")
add_assistant_message("6.8 hours avg")  → LLMMessage(role="assistant", content="...")
add_tool_result("query_logs", "Mon 7.5, Tue 6.0...")  → LLMMessage(role="tool", content="[Tool: query_logs]\nMon 7.5...")
```

The `tool` role tells the LLM: "This is data from a database query, not something a human said." The LLM treats tool results as factual data to reference in its answer.

**`list(self._messages)` — Defensive Copy**
```python
def get_messages(self) -> list[LLMMessage]:
    return list(self._messages)
```
- Returns a COPY of the list, not the original
- If the caller modifies the returned list, the internal `_messages` isn't affected
- Common defensive pattern for mutable internal state

**Why 20 Messages?**
- 20 messages ≈ 10 back-and-forth exchanges (user + assistant)
- At ~100 tokens per message = ~2000 tokens of history
- Leaves room in the context window for: system prompt (~200), tool results (~500), and response (~500)
- Total: ~3200 tokens — fits comfortably in any LLM's context window

---

<a name="long-term"></a>
## 3. File 2: `long_term.py` — Persistent Insights

### Type This Code: `backend/app/modules/ai/agents/memory/long_term.py`

```python
# ============================================================================
# Agent Memory — Long-Term (Persistent Key Insights)
# ============================================================================
# WHAT THIS FILE DOES:
#   Stores important insights about the user that persist across sessions.
#   "Shreya is vegetarian" "Shreya is trying to improve sleep"
#
# STORAGE: Redis hash (fast access, 24h TTL refreshed on access)
# ============================================================================

import json
from uuid import UUID

import redis.asyncio as redis

from app.shared.logging import get_logger

logger = get_logger(__name__)

MAX_INSIGHTS = 20
REDIS_TTL = 86400  # 24 hours — refreshed on every access


class LongTermMemory:
    """
    Persistent memory that survives across conversation sessions.

    Stores key-value insights about the user:
    - "dietary_preference": "vegetarian"
    - "health_goal": "improve sleep to 8 hours"
    - "pattern_noticed": "mood drops on days with < 6 hours sleep"

    Usage:
        memory = LongTermMemory(redis_client)
        await memory.save_insight(user_id, "dietary_preference", "vegetarian")
        insights = await memory.get_all_insights(user_id)
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def save_insight(self, user_id: UUID, key: str, value: str) -> None:
        """
        Save a key insight about the user.
        If the key already exists, it's overwritten with the new value.
        """
        redis_key = f"memory:{user_id}:insights"

        try:
            await self.redis.hset(redis_key, key, value)
            await self.redis.expire(redis_key, REDIS_TTL)

            # Trim to MAX_INSIGHTS if too many
            count = await self.redis.hlen(redis_key)
            if count > MAX_INSIGHTS:
                all_keys = await self.redis.hkeys(redis_key)
                to_remove = all_keys[: count - MAX_INSIGHTS]
                if to_remove:
                    await self.redis.hdel(redis_key, *to_remove)

            logger.debug("insight_saved", user_id=str(user_id), key=key)
        except Exception:
            logger.warning("insight_save_error", user_id=str(user_id), key=key)

    async def get_all_insights(self, user_id: UUID) -> dict[str, str]:
        """Get all stored insights for a user. Refreshes TTL on access."""
        redis_key = f"memory:{user_id}:insights"

        try:
            insights = await self.redis.hgetall(redis_key)
            if insights:
                await self.redis.expire(redis_key, REDIS_TTL)
            return insights or {}
        except Exception:
            logger.warning("insight_get_error", user_id=str(user_id))
            return {}

    async def get_insight(self, user_id: UUID, key: str) -> str | None:
        """Get a specific insight by key."""
        redis_key = f"memory:{user_id}:insights"
        try:
            return await self.redis.hget(redis_key, key)
        except Exception:
            return None

    async def remove_insight(self, user_id: UUID, key: str) -> None:
        """Remove a specific insight."""
        redis_key = f"memory:{user_id}:insights"
        try:
            await self.redis.hdel(redis_key, key)
        except Exception:
            pass

    async def format_for_prompt(self, user_id: UUID) -> str:
        """
        Format all insights into a string for the LLM prompt.

        Injected into the system prompt so the agent
        "remembers" things about the user across sessions.
        """
        insights = await self.get_all_insights(user_id)

        if not insights:
            return ""

        lines = ["KNOWN FACTS ABOUT THIS USER:"]
        for key, value in insights.items():
            lines.append(f"- {key}: {value}")

        return "\n".join(lines)
```

### Key Concepts

**Redis Hash — Key-Value Map**
```python
await self.redis.hset(redis_key, key, value)   # Set one field
await self.redis.hgetall(redis_key)             # Get ALL fields
await self.redis.hlen(redis_key)                # Count fields
await self.redis.hdel(redis_key, *to_remove)    # Delete fields
```

Redis hashes store multiple key-value pairs under one Redis key:

```
Redis key: "memory:uuid-001:insights"
  ├── dietary_preference: "vegetarian"
  ├── health_goal: "improve sleep to 8 hours"
  ├── exercise_pattern: "runs 3x per week"
  └── pattern_noticed: "mood drops with < 6h sleep"
```

**TTL Refreshed on Access**
```python
await self.redis.expire(redis_key, REDIS_TTL)  # Reset 24h timer
```
- Every time insights are READ, the 24-hour timer resets
- Active users' data stays alive indefinitely
- Inactive users' data expires after 24 hours (cleanup)
- This is called "sliding TTL" or "touch-to-refresh"

**MAX_INSIGHTS = 20 (Trim Old Ones)**
```python
count = await self.redis.hlen(redis_key)
if count > MAX_INSIGHTS:
    all_keys = await self.redis.hkeys(redis_key)
    to_remove = all_keys[: count - MAX_INSIGHTS]
    await self.redis.hdel(redis_key, *to_remove)
```
- 20 insights per user maximum
- When exceeded, oldest are removed (FIFO)
- Prevents memory bloat for chatty users
- 20 insights ≈ 20 lines in the system prompt ≈ ~200 tokens

**`format_for_prompt()` — System Prompt Injection**
```
KNOWN FACTS ABOUT THIS USER:
- dietary_preference: vegetarian
- health_goal: improve sleep to 8 hours
- exercise_pattern: runs 3x per week
- pattern_noticed: mood drops on days with < 6 hours sleep
```

This text is injected into the system prompt at the start of every chat session. The LLM sees it as established facts about the user — no need to re-discover them.

---

<a name="integration"></a>
## 4. How Memory Integrates with the Agent

```
NEW CHAT SESSION STARTS:
  │
  ▼
HealthCoachAgent.create(session, redis, user_id, user):
  │
  ├── long_term = LongTermMemory(redis)
  │   └── insights = await long_term.format_for_prompt(user_id)
  │       → "KNOWN FACTS: vegetarian, wants better sleep, runs 3x/week"
  │
  ├── short_term = ShortTermMemory(max_messages=20)
  │   └── (empty — fresh conversation)
  │
  ├── system_prompt = HEALTH_COACH_SYSTEM.render(user_name=...) + insights
  │   → "You are a health coach for Shreya... KNOWN FACTS: vegetarian..."
  │
  └── agent = BaseAgent(llm, tools, system_prompt, short_term)

DURING CONVERSATION:
  User: "What should I eat for iron?"
  │
  ▼
  agent.run("What should I eat for iron?")
    │
    ├── short_term.add_user_message("What should I eat for iron?")
    │
    ├── messages = [system_prompt] + short_term.get_messages()
    │   → system includes "KNOWN FACTS: vegetarian" (from long-term)
    │   → messages includes "What should I eat for iron?" (from short-term)
    │
    ├── LLM sees: user is vegetarian (long-term) + wants iron advice (short-term)
    │   → "Since you're vegetarian, try spinach, lentils, fortified cereals..."
    │
    └── short_term.add_assistant_message("Since you're vegetarian...")

DURING TOOL USE:
  [THINK] "Let me check their recent food data"
  [ACT]   tool: query_logs(habit_name="all", days=7)
  [OBSERVE] short_term.add_tool_result("query_logs", "Water: 7, Sleep: 6.8...")
  → LLM sees tool result in the conversation history → uses it in answer
```

---

<a name="design-decisions"></a>
## 5. Design Decisions

### Design Decision: Redis Hash vs PostgreSQL for Long-Term Memory

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Long-Term Memory Storage                          │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Redis hash with sliding TTL                                │
│                                                                     │
│  WHY:                                                               │
│  • Fast reads — insights are loaded at the start of every chat      │
│    session. Redis: <1ms. PostgreSQL: ~5ms.                          │
│  • Key-value map — Redis HSET/HGETALL is perfect for named insights │
│  • Sliding TTL — auto-cleanup for inactive users                    │
│  • Already have Redis — no new infrastructure                       │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. PostgreSQL table (user_insights)                                │
│     ⚠️ Works but slower reads. Would use for permanent backup.     │
│  2. Vector-based memory (embed insights, search by relevance)       │
│     ⚠️ Better for large memory stores (100+ insights). Overkill    │
│        for 20 key-value pairs. Used by LangChain's memory module.  │
│  3. In-memory dict per user                                         │
│     ❌ Lost on server restart, not shared across workers            │
│                                                                     │
│  INTERVIEW TIP: "We use Redis hashes for long-term memory —        │
│  fast reads at chat session start, sliding TTL for cleanup, and     │
│  key-value structure matching our insight format. For a production   │
│  system with hundreds of insights, we'd use vector-based memory     │
│  retrieval."                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 6. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Sliding window buffer** | Keep last N items, drop oldest when full | ShortTermMemory |
| 2 | **`list.pop(0)`** | Remove first element (oldest in a FIFO buffer) | `_add()` |
| 3 | **Defensive copy** | `return list(self._messages)` prevents external mutation | `get_messages()` |
| 4 | **Three message roles** | user, assistant, tool — LLM treats each differently | `add_*_message()` |
| 5 | **Redis HSET/HGETALL** | Store/retrieve a hash (key-value map) | LongTermMemory |
| 6 | **Sliding TTL** | Reset TTL on every access — active users stay alive | `expire()` on read |
| 7 | **HLEN + HDEL trim** | Count entries, delete oldest if over limit | `save_insight()` |
| 8 | **`format_for_prompt()`** | Convert insights to text for system prompt injection | Agent setup |
| 9 | **Cross-session persistence** | User says "I'm vegetarian" → agent remembers next week | Long-term memory |
| 10 | **Token budgeting** | 20 messages × 100 tokens = 2000 tokens for history | `max_messages=20` |

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: How does your agent remember context within a conversation?
**A:** "Short-term memory — a sliding window buffer of the last 20 messages. Every user message, assistant response, and tool result is stored as an `LLMMessage`. When the buffer is full, the oldest message is dropped. These messages are prepended to every LLM call, so the agent knows what was discussed earlier. 20 messages ≈ 2000 tokens — a predictable token budget that leaves room for the system prompt and response."

### Q2: How does the agent remember things across sessions?
**A:** "Long-term memory stored in a Redis hash. When the agent notices something important ('user is vegetarian', 'user wants to improve sleep'), it saves it as a key-value insight. At the start of each new chat session, all insights are loaded and injected into the system prompt: 'KNOWN FACTS: dietary_preference=vegetarian, health_goal=improve sleep.' The LLM sees these as established context — no need to rediscover them."

### Q3: Why a sliding window instead of summarizing old messages?
**A:** "Simplicity and predictability. A sliding window has a fixed token cost (20 × ~100 = ~2000 tokens). Summarization would require an extra LLM call per conversation to compress old messages — adding latency and cost. For a health coaching chat, 10 back-and-forth exchanges (20 messages) covers the typical session. If sessions were longer (100+ messages), we'd implement summarization."

### Q4: How is long-term memory different from the database chat history?
**A:** "The database (`ai_chat_messages` table) stores the COMPLETE chat history — every message ever sent. It's for display ('show past conversations') and audit. Long-term memory stores KEY INSIGHTS — extracted facts like 'vegetarian' or 'runs 3x/week.' The database is raw data; long-term memory is distilled knowledge. Loading 200 past messages into a prompt would be expensive and noisy. Loading 20 one-line insights is cheap and targeted."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 10a: Agent Tools](./phase4-part10a-ai-agent-tools.md) |
| ➡️ Next | [Phase 4 Part 10c: ReAct Loop ★★★](./phase4-part10c-ai-agent-react-loop.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Agent Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 10a | ✅ Done | Agent Tools |
| **10b** | ✅ **You are here** | Agent Memory |
| 10c | ⬜ Next | ReAct Loop ★★★ |
| 10d | ⬜ | Agent Connections & Flows |

---

**End of Phase 4 Part 10b: Agent Memory**

*The agent now has a brain — short-term for conversation context, long-term for persistent knowledge. Next: the ReAct loop — the beating heart of the agent, where thinking, acting, and observing happen in a loop.*
