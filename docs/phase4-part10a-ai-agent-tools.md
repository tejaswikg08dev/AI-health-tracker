# 🧠 Phase 4 Part 10a: AI Agent — Tools

> **"A tool is a function the AI can call. The LLM sees the tool's name, description, and parameter schema — then decides WHEN to call it and WHAT arguments to pass. The tool executes, returns real data, and the LLM uses that data to answer. This is what makes agents powerful."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 10a (Agent Tools) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.3 — AI Agent + Tools |
| **Previous** | [phase4-part10-ai-agents-overview.md](./phase4-part10-ai-agents-overview.md) |
| **Next** | [phase4-part10b-ai-agent-memory.md](./phase4-part10b-ai-agent-memory.md) |
| **Files in This Doc** | 2 files shown in full (base_tool.py, query_logs.py) + 4 tools summarized |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (abstract tool interface, JSON Schema, cross-module data access) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: base_tool.py — Abstract Tool Interface](#base-tool)
3. [File 2: query_logs.py — Representative Tool (Full Source)](#query-logs)
4. [The Other 4 Tools (Summary)](#other-tools)
5. [How the LLM Sees Tools](#llm-view)
6. [Design Decisions](#design-decisions)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

6 files — 1 abstract base + 5 concrete tools:

| File | Tool Name | What It Does | Data Source |
|------|-----------|-------------|------------|
| `base_tool.py` | — | Abstract interface all tools implement | — |
| `query_logs.py` | `query_logs` | Fetch habit log data | habit_logs table |
| `get_analytics.py` | `get_analytics` | Get streaks, weekly summary, trends | Analytics service (cached) |
| `correlate.py` | `correlate` | Find habit-to-habit correlations | Analytics service |
| `search_docs.py` | `search_docs` | RAG vector search on documents | pgvector (Part 09) |
| `create_plan.py` | `create_plan` | Generate an action plan | LLM-generated (no DB) |

### How Tools Fit in the Agent

```
User: "How was my sleep this week?"
  │
  ▼
Agent (ReAct loop):
  [THINK] "I need sleep data" → decides to use query_logs tool
  [ACT]   tool_call: query_logs(habit_name="Sleep", days=7)
            │
            ▼
          QueryLogsTool.execute(habit_name="Sleep", days=7)
            → LogRepository.get_logs_for_range(user_id, start, end, habit_id)
            → Format results as readable text
            → Return: "Sleep data: Mon 7.5h, Tue 6.0h, Wed 8.0h..."
            │
  [OBSERVE] Agent sees the tool result
  [ANSWER]  "Your sleep averaged 6.8 hours this week..."
```

---

<a name="base-tool"></a>
## 2. File 1: `base_tool.py` — Abstract Tool Interface

### Type This Code: `backend/app/modules/ai/agents/tools/base_tool.py`

```python
# ============================================================================
# Agent Tools — Abstract Base Tool
# ============================================================================
# A tool is a function the AI agent can call to fetch real data.
# The LLM sees: name, description, parameters_schema
# The agent executes: execute(**kwargs) → string result
# ============================================================================

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.

    Every tool must define:
    - name: unique identifier (e.g., "query_logs")
    - description: what the tool does (LLM reads this to decide when to use it)
    - parameters_schema: JSON Schema for the tool's parameters
    - execute(): the actual function that runs when the tool is called
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (lowercase, underscored)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """
        What this tool does — the LLM reads this to decide when to use it.
        Be specific: "Get the user's habit log data for a specific date range"
        Not vague: "Get data"
        """
        ...

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema defining the tool's parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool with the given arguments.
        Returns a string — the LLM will interpret this in its response.
        """
        ...

    def to_openai_schema(self) -> dict:
        """
        Convert to OpenAI function calling format.
        This format is the industry standard — works with all LLM providers.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }
```

### Key Concepts

**`@property` + `@abstractmethod` Combined**
```python
@property
@abstractmethod
def name(self) -> str:
    ...
```
- `@property` — access as `tool.name` (no parentheses)
- `@abstractmethod` — subclass MUST implement it
- Both decorators stack — the subclass provides a property that returns the name

**`to_openai_schema()` — The Tool's "Resume"**

This is what the LLM sees. The format matches the OpenAI function calling specification — now the industry standard:

```json
{
    "type": "function",
    "function": {
        "name": "query_logs",
        "description": "Get the user's habit log data for a specific date range",
        "parameters": {
            "type": "object",
            "properties": {
                "habit_name": {"type": "string", "description": "Name of the habit"},
                "days": {"type": "integer", "description": "Number of past days"}
            },
            "required": ["habit_name"]
        }
    }
}
```

The LLM reads this schema and decides: "The user asked about sleep → I should call `query_logs` with `habit_name='Sleep'` and `days=7`."

**`execute()` Returns a String**
- Not JSON, not a dict — a plain readable string
- The LLM receives this text and incorporates it into its answer
- Example: `"Sleep data for last 7 days:\n  Sep 20 | Sleep: 7.5 hours\n  Sep 21 | Sleep: 6.0 hours..."`

---

<a name="query-logs"></a>
## 3. File 2: `query_logs.py` — Representative Tool (Full Source)

This is the most used tool — every question about "how much", "how was", "what did I" uses it.

### Type This Code: `backend/app/modules/ai/agents/tools/query_logs.py`

```python
# ============================================================================
# Agent Tool — Query Habit Logs
# ============================================================================
# WHEN THE AGENT USES IT: "How much water did I drink this week?"
#   Agent thinks: "I need the user's water log data" → calls this tool
# ============================================================================

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.logs.repository import LogRepository
from app.modules.habits.repository import HabitRepository
from app.shared.date_utils import today_utc


class QueryLogsTool(BaseTool):
    """Fetch habit log data for a user within a date range."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    @property
    def name(self) -> str:
        return "query_logs"

    @property
    def description(self) -> str:
        return (
            "Get the user's habit log data for a specific date range. "
            "Returns daily values for the requested habit(s). "
            "Use this when the user asks about their data, progress, or specific numbers."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "habit_name": {
                    "type": "string",
                    "description": "Name of the habit to query (e.g., 'Water Intake', 'Sleep'). "
                                   "Use 'all' to get all habits.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of past days to include (default: 7)",
                    "default": 7,
                },
            },
            "required": ["habit_name"],
        }

    async def execute(self, **kwargs) -> str:
        habit_name = kwargs.get("habit_name", "all")
        days = min(kwargs.get("days", 7), 90)  # Cap at 90 days

        log_repo = LogRepository(self.session)
        habit_repo = HabitRepository(self.session)

        start_date = today_utc() - timedelta(days=days - 1)
        end_date = today_utc()

        # Find the habit if a specific one is requested
        habit_id = None
        if habit_name.lower() != "all":
            habits = await habit_repo.get_user_habits(self.user_id)
            for h in habits:
                if habit_name.lower() in h.name.lower():
                    habit_id = h.id
                    break
            if not habit_id:
                return f"No habit found matching '{habit_name}'. Available habits: {', '.join(h.name for h in habits)}"

        logs = await log_repo.get_logs_for_range(
            self.user_id, start_date, end_date, habit_id
        )

        if not logs:
            return f"No log data found for the last {days} days."

        # Format results as readable text
        habits_data = await habit_repo.get_user_habits(self.user_id)
        habit_names = {str(h.id): h.name for h in habits_data}
        habit_units = {str(h.id): h.unit for h in habits_data}

        lines = [f"Habit log data for the last {days} days ({start_date} to {end_date}):\n"]
        for log in logs:
            name = habit_names.get(str(log.habit_id), "Unknown")
            unit = habit_units.get(str(log.habit_id), "")
            value = log.value_numeric or log.value_scale or ("Yes" if log.value_boolean else "No")
            lines.append(f"  {log.log_date} | {name}: {value} {unit}")

        return "\n".join(lines)
```

### Line-by-Line Walkthrough

**Constructor — Receives Session + User ID**
```python
def __init__(self, session: AsyncSession, user_id: UUID):
    self.session = session
    self.user_id = user_id
```
- The HealthCoachAgent creates each tool with the current session and user_id
- Tools use these to query the database securely (user-scoped)

**Fuzzy Habit Name Matching**
```python
if habit_name.lower() in h.name.lower():
    habit_id = h.id
    break
```
- The LLM might say `habit_name="Sleep"` but the actual habit is "Sleep Hours"
- `in` checks if the LLM's guess is a SUBSTRING of the real name
- Case-insensitive: `"sleep" in "sleep hours"` → True
- If no match: returns helpful error listing available habits

**Graceful "No Data" Response**
```python
if not logs:
    return f"No log data found for the last {days} days."
```
- The agent sees this text and tells the user: "You haven't logged any sleep data recently"
- Better than an empty response or a crash

**Formatted Output**
```
Habit log data for the last 7 days (2026-09-20 to 2026-09-26):

  2026-09-20 | Water Intake: 7 glasses
  2026-09-21 | Water Intake: 8 glasses
  2026-09-22 | Water Intake: 6 glasses
  ...
```
- Plain text that the LLM can easily parse and reference in its answer
- Date + habit name + value + unit — all the context the LLM needs

---

<a name="other-tools"></a>
## 4. The Other 4 Tools (Summary)

All follow the same pattern as `QueryLogsTool`. Type them from their source files.

### `get_analytics.py` — Get Analytics Data
```python
class GetAnalyticsTool(BaseTool):
    name = "get_analytics"
    description = "Get computed analytics: streaks, weekly summary, completion rates, or trends."
    parameters = {"type": {"type": "string", "enum": ["streaks", "weekly", "completion", "trend"]}}

    async def execute(self, **kwargs) -> str:
        # Calls AnalyticsService (which uses cache-aside)
        # Returns formatted analytics text
```

### `correlate.py` — Find Correlations
```python
class CorrelateTool(BaseTool):
    name = "correlate"
    description = "Find correlations between habits. Shows which habits affect each other."
    parameters = {"days": {"type": "integer", "default": 30}}

    async def execute(self, **kwargs) -> str:
        # Calls AnalyticsService.get_correlations()
        # Returns: "Sleep ↔ Mood: r=0.72 (strong positive)\n..."
```

### `search_docs.py` — RAG Document Search
```python
class SearchDocsTool(BaseTool):
    name = "search_docs"
    description = "Search the user's uploaded documents for relevant information."
    parameters = {"query": {"type": "string"}}

    async def execute(self, **kwargs) -> str:
        # Calls Retriever.retrieve() (Part 09b)
        # Returns formatted context with source citations
```

### `create_plan.py` — Generate Action Plan
```python
class CreatePlanTool(BaseTool):
    name = "create_plan"
    description = "Generate a personalized action plan for a health goal."
    parameters = {"goal": {"type": "string"}, "timeframe": {"type": "string", "default": "1 week"}}

    async def execute(self, **kwargs) -> str:
        # Uses LLM directly to generate a structured plan
        # No DB access — pure LLM generation
        # Returns: "Plan to improve sleep:\n1. Set bedtime alarm at 10 PM\n2. ..."
```

---

<a name="llm-view"></a>
## 5. How the LLM Sees Tools

The agent's system prompt includes all tool schemas. Here's what the LLM actually sees:

```
You have access to the following tools:

1. query_logs: Get the user's habit log data for a specific date range.
   Returns daily values for the requested habit(s).
   Parameters:
     - habit_name (string, required): Name of the habit to query
     - days (integer, optional): Number of past days (default: 7)

2. get_analytics: Get computed analytics: streaks, weekly summary,
   completion rates, or trends.
   Parameters:
     - type (string, required): One of "streaks", "weekly", "completion", "trend"

3. correlate: Find correlations between habits.
   Parameters:
     - days (integer, optional): Period to analyze (default: 30)

4. search_docs: Search the user's uploaded documents.
   Parameters:
     - query (string, required): What to search for

5. create_plan: Generate a personalized action plan.
   Parameters:
     - goal (string, required): The health goal
     - timeframe (string, optional): Timeline (default: "1 week")

To use a tool, respond with a tool call in this format:
TOOL_CALL: {"name": "query_logs", "arguments": {"habit_name": "Sleep", "days": 7}}
```

The LLM reads this, understands what each tool does, and decides which one to call based on the user's question.

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision: Tool Description Quality

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Tool Description Strategy                         │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Detailed, specific descriptions with usage guidance        │
│                                                                     │
│  EXAMPLES:                                                          │
│  BAD:  "Get data"                                                   │
│  GOOD: "Get the user's habit log data for a specific date range.    │
│         Returns daily values for the requested habit(s). Use this   │
│         when the user asks about their data, progress, or numbers." │
│                                                                     │
│  WHY IT MATTERS:                                                    │
│  The LLM decides which tool to call based ONLY on the description.  │
│  A vague description → LLM picks the wrong tool → bad answer.      │
│  A specific description → LLM picks correctly → accurate answer.   │
│                                                                     │
│  THE "Use this when..." CLAUSE:                                     │
│  Tells the LLM WHEN to use the tool. Without it, the LLM might     │
│  call query_logs when the user asks a general knowledge question    │
│  (wasting a tool call). "Use this when the user asks about their    │
│  data" → LLM only calls it for data questions.                     │
│                                                                     │
│  INTERVIEW TIP: "Tool descriptions are prompt engineering for the   │
│  agent. The LLM decides tool selection based entirely on the        │
│  description text. We include 'Use this when...' guidance so the    │
│  agent picks the right tool for each question type."                │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`@property` + `@abstractmethod`** | Required read-only property in subclasses | `name`, `description`, `parameters_schema` |
| 2 | **JSON Schema** | Describes tool parameters (type, required, default) | `parameters_schema` |
| 3 | **`to_openai_schema()`** | Convert tool to industry-standard format | Agent sends to LLM |
| 4 | **`execute()` returns string** | Tool result as readable text for the LLM | All tool implementations |
| 5 | **Fuzzy name matching** | `"sleep" in "Sleep Hours"` — handles LLM imprecision | `query_logs.py` |
| 6 | **Cross-module data access** | Tool uses LogRepository + HabitRepository | `query_logs.py` |
| 7 | **Safety caps** | `min(days, 90)` — prevent LLM requesting absurd ranges | `query_logs.py` |
| 8 | **Helpful error messages** | "No habit matching 'X'. Available: Water, Sleep..." | `execute()` |
| 9 | **User-scoped queries** | Tools receive `user_id` — always filter by owner | Constructor |
| 10 | **Description = prompt engineering** | Quality of description determines tool selection accuracy | All tool descriptions |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: How does the agent know which tool to use?
**A:** "The agent's system prompt includes each tool's name, description, and parameter schema in OpenAI function calling format. The LLM reads these descriptions and matches them to the user's question. 'How much water did I drink?' matches `query_logs` (description: 'Get habit log data'). 'What does my nutrition guide say?' matches `search_docs` (description: 'Search uploaded documents'). The quality of the description directly determines tool selection accuracy — it's prompt engineering for agents."

### Q2: Why does execute() return a string, not structured data?
**A:** "The result goes back to the LLM as a new message in the conversation. The LLM interprets natural language better than JSON. A string like 'Sleep data: Mon 7.5h, Tue 6.0h, avg 6.8h' is immediately usable in the response. Structured JSON would require the LLM to parse keys and values — adding unnecessary complexity. The tool does the data access; the LLM does the interpretation."

### Q3: How do tools handle LLM imprecision?
**A:** "The LLM might say `habit_name='Sleep'` when the actual habit is 'Sleep Hours'. We use fuzzy matching: `if 'sleep' in 'sleep hours'` — case-insensitive substring check. If no match is found, we return a helpful error listing all available habits: 'No habit matching Sleep. Available: Water Intake, Sleep Hours, Mood.' The LLM reads this, self-corrects, and retries with the correct name."

### Q4: How do you prevent the LLM from requesting too much data?
**A:** "Safety caps. `days = min(kwargs.get('days', 7), 90)` ensures the tool never queries more than 90 days regardless of what the LLM requests. Without this, the LLM might request `days=10000`, producing a massive response that wastes tokens and overwhelms the context window. The cap is invisible to the LLM — it just gets 90 days of data at most."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 10: AI Agents Overview](./phase4-part10-ai-agents-overview.md) |
| ➡️ Next | [Phase 4 Part 10b: Agent Memory](./phase4-part10b-ai-agent-memory.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Agent Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **10a** | ✅ **You are here** | Agent Tools |
| 10b | ⬜ Next | Agent Memory |
| 10c | ⬜ | ReAct Loop ★★★ |
| 10d | ⬜ | Agent Connections & Flows |

---

**End of Phase 4 Part 10a: Agent Tools**

*5 tools give the agent its capabilities — data access, analytics, correlations, document search, and plan generation. Next: the memory system that gives the agent context across messages and sessions.*
