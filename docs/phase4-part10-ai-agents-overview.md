# 🧠 Phase 4 Part 10: AI — Agents Overview

> **"An agent doesn't just answer — it THINKS. It decides what tool to use, executes it, observes the result, and reasons about what to do next. This is the ReAct pattern: Reason + Act, in a loop, until the answer is complete. This is how LangChain, CrewAI, and AutoGen work under the hood."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 10 (AI Module — Agents Overview) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.3 — AI Agent + Tools |
| **Previous** | [phase4-part09c-ai-rag-connections-and-flows.md](./phase4-part09c-ai-rag-connections-and-flows.md) |
| **Next** | [phase4-part10a-ai-agent-tools.md](./phase4-part10a-ai-agent-tools.md) |
| **Files** | 10 files (base_agent, health_coach, 5 tools, 2 memory, base_tool) |
| **Sub-Parts** | 4 documents (10a–10d) |
| **Difficulty** | ★★★ HARD (agent reasoning loop, tool orchestration, memory management) |

---

## 📖 Table of Contents

1. [What Is an AI Agent?](#what-is-agent)
2. [The ReAct Pattern — How It Works](#react)
3. [The 5 Agent Tools](#tools)
4. [Agent Memory — Short-Term & Long-Term](#memory)
5. [The Health Coach Agent](#health-coach)
6. [File List & Sub-Part Roadmap](#file-list)
7. [Architecture Diagram](#architecture)
8. [Design Decisions](#design-decisions)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="what-is-agent"></a>
## 1. What Is an AI Agent?

A regular chatbot generates text from its training data. An **agent** can also **take actions** — query databases, call APIs, run calculations — and use the results to formulate better answers.

```
REGULAR CHATBOT (one LLM call):
  User: "How was my sleep this week?"
  AI: "I don't have access to your data. Generally, adults need 7-9 hours..."
  ← Useless. No access to the user's actual data.

AI AGENT (multiple LLM calls + tool use):
  User: "How was my sleep this week?"

  [THINK 1] "I need to check sleep data for this week"
  [ACT 1]   tool: query_logs(habit_name="Sleep", days=7)
  [OBSERVE]  Sleep: Mon=7.5, Tue=6.0, Wed=8.0, Thu=5.5, Fri=7.0, Sat=6.5, Sun=7.2

  [THINK 2] "I should compare to last week for context"
  [ACT 2]   tool: get_analytics(type="weekly_summary")
  [OBSERVE]  This week avg: 6.8h, Last week avg: 7.2h, Change: -5.6%

  [THINK 3] "I have enough data to give a helpful answer"
  [ANSWER]   "Your sleep averaged 6.8 hours this week, down 5.6% from last
              week's 7.2 hours. Thursday was the worst night at 5.5 hours.
              Your best night was Wednesday at 8 hours. Consider going to
              bed 30 minutes earlier on work nights."
  ← Specific, data-driven, actionable.
```

### Agent vs Chatbot — The Key Difference

| Feature | Chatbot | Agent |
|---------|---------|-------|
| LLM calls | 1 | 1–10 (loop) |
| Data access | None (training data only) | Yes (via tools) |
| Reasoning | Implicit (in one shot) | Explicit (Think → Act → Observe) |
| Tools | None | query_logs, correlate, search_docs, etc. |
| Memory | None or stateless | Short-term (conversation) + Long-term (DB) |
| Answer quality | Generic | Personalized, data-driven |

---

<a name="react"></a>
## 2. The ReAct Pattern — How It Works

### The Loop

```
┌────────────────────────────────────────────────────────────────┐
│                    ReAct LOOP                                   │
│                                                                  │
│  User message: "Why is my mood low this week?"                  │
│                                                                  │
│  ┌──────────┐                                                    │
│  │  THINK   │ LLM: "I need to check mood data for this week"    │
│  └────┬─────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │   ACT    │ tool_call: query_logs(habit="Mood", days=7)        │
│  └────┬─────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │ OBSERVE  │ Result: Mood scores: 8, 7, 5, 4, 5, 6, 5         │
│  └────┬─────┘ Average: 5.7 (down from 7.2 last week)            │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │  THINK   │ LLM: "Mood dropped. What else changed this week?" │
│  └────┬─────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │   ACT    │ tool_call: correlate(habit_a="Mood", days=30)      │
│  └────┬─────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │ OBSERVE  │ Correlations: Sleep↔Mood r=0.72 (strong +)         │
│  └────┬─────┘ This week sleep avg: 5.8h (down from 7.5h)        │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │  THINK   │ LLM: "Sleep dropped → Mood dropped. Let me check  │
│  └────┬─────┘ if they have relevant documents"                   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │   ACT    │ tool_call: search_docs(query="sleep and mood")     │
│  └────┬─────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │ OBSERVE  │ Found: "Sleep Guide.pdf" — "Poor sleep quality     │
│  └────┬─────┘ directly impacts serotonin production..."          │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │  THINK   │ LLM: "I have enough info to give a comprehensive   │
│  └────┬─────┘ answer with data + science"                        │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐                                                    │
│  │  ANSWER  │ "Your mood dropped because your sleep dropped.     │
│  │          │  This week: mood avg 5.7 (down from 7.2), sleep    │
│  │          │  avg 5.8h (down from 7.5h). These are strongly     │
│  │          │  correlated (r=0.72). Your sleep guide notes that   │
│  │          │  poor sleep reduces serotonin production.            │
│  │          │  Suggestion: try getting back to 7+ hours tonight." │
│  └──────────┘                                                    │
│                                                                  │
│  Total: 3 tool calls, 4 LLM reasoning steps                     │
│  Max allowed: 5 tool calls (safety limit)                        │
└────────────────────────────────────────────────────────────────┘
```

### How the LLM Knows About Tools

The tools are described in the system prompt:

```
You have access to the following tools:

1. query_logs: Get habit log data for a date range
   Parameters: habit_name (string), days (integer)

2. get_analytics: Get streaks, weekly summary, or trends
   Parameters: type (string: "streaks"|"weekly"|"completion"|"trend")

3. correlate: Find correlations between habits
   Parameters: habit_a (string, optional), days (integer)

4. search_docs: Search user's uploaded documents
   Parameters: query (string)

5. create_plan: Generate an action plan
   Parameters: goal (string), timeframe (string)

To use a tool, respond with:
TOOL_CALL: {"name": "query_logs", "arguments": {"habit_name": "Sleep", "days": 7}}

After I show you the tool result, continue reasoning.
When you have enough information, give your final answer.
```

The LLM outputs structured tool calls. The agent parses them, executes the tool, and feeds the result back.

---

<a name="tools"></a>
## 3. The 5 Agent Tools

| # | Tool | What It Does | Data Source | Example Use |
|---|------|-------------|-------------|------------|
| 1 | **`query_logs`** | Fetch habit log data | habit_logs table | "How much water did I drink this week?" |
| 2 | **`get_analytics`** | Get computed analytics | Analytics service | "Am I improving at meditation?" |
| 3 | **`correlate`** | Find habit correlations | Analytics + Python | "What affects my mood?" |
| 4 | **`search_docs`** | RAG vector search | pgvector (document chunks) | "What does my guide say about iron?" |
| 5 | **`create_plan`** | Generate action plan | LLM-generated | "Make me a plan to sleep better" |

### Tool Architecture

```
┌─── BaseTool (abc.ABC) ───────────────────────────────┐
│  name: str              ← Tool identifier              │
│  description: str       ← What the tool does            │
│  parameters: dict       ← JSON Schema for arguments     │
│  + execute(**args) → str ← @abstractmethod               │
└──────────┬──────────────────────────────────────────────┘
           │ implements
    ┌──────┼──────┬──────────┬──────────┬─────────────┐
    │      │      │          │          │             │
┌───▼──┐┌──▼───┐┌─▼────┐┌───▼────┐┌────▼──────────┐
│query ││get_  ││corre-││search ││create_plan   │
│_logs ││analy-││late  ││_docs  ││              │
│      ││tics  ││      ││       ││ LLM generates│
│DB    ││Cache ││Stats ││pgvec- ││ action steps │
│query ││/SQL  ││      ││tor    ││              │
└──────┘└──────┘└──────┘└───────┘└──────────────┘
```

Each tool:
1. Inherits from `BaseTool`
2. Defines `name`, `description`, `parameters` (as JSON Schema)
3. Implements `execute(**kwargs) → str` — the actual data fetching
4. Returns a string (the agent feeds this text back to the LLM)

---

<a name="memory"></a>
## 4. Agent Memory — Short-Term & Long-Term

### Short-Term Memory (Conversation)

```
┌─── ShortTermMemory ───────────────────────────────────────────┐
│  Stores: current chat session messages                         │
│  Lifetime: until session ends (in-memory)                      │
│  Purpose: "What did the user ask 3 messages ago?"              │
│                                                                 │
│  Messages:                                                      │
│  [system] "You are a health coach..."                          │
│  [user]   "How's my sleep?"                                    │
│  [assistant] "Your sleep averaged 6.8h..."                     │
│  [user]   "What about compared to last month?"                 │
│  [assistant] "Last month you averaged 7.1h, so this week..."   │
│                                                                 │
│  Without this: every message would be treated as a new          │
│  conversation — the AI wouldn't remember "my sleep" refers      │
│  to the topic from 3 messages ago.                              │
└───────────────────────────────────────────────────────────────┘
```

### Long-Term Memory (Database)

```
┌─── LongTermMemory ────────────────────────────────────────────┐
│  Stores: past insights, user preferences, important context    │
│  Lifetime: permanent (PostgreSQL — ai_insights table)          │
│  Purpose: "What did we talk about last week?"                  │
│                                                                 │
│  Records:                                                       │
│  [2026-09-19] "User wants to improve sleep quality"            │
│  [2026-09-19] "Recommended: reduce screen time after 9 PM"     │
│  [2026-09-22] "User reported sleeping better on exercise days"  │
│                                                                 │
│  Injected into system prompt:                                   │
│  "PAST CONTEXT: The user previously mentioned wanting to        │
│   improve sleep. You recommended reducing screen time."         │
│                                                                 │
│  Without this: every week the AI starts from scratch —          │
│  no continuity, no follow-up on past recommendations.           │
└───────────────────────────────────────────────────────────────┘
```

---

<a name="health-coach"></a>
## 5. The Health Coach Agent

`HealthCoachAgent` extends `BaseAgent` with health-specific configuration:

```python
class HealthCoachAgent:
    """
    Pre-configured agent with:
    1. Health coach system prompt (persona, rules, tone)
    2. All 5 health tools registered
    3. Long-term memory loaded from DB
    4. Short-term memory for the conversation
    """

    @classmethod
    async def create(cls, session, redis, user_id, user):
        # Load tools
        tools = [
            QueryLogsTool(session, user_id),
            GetAnalyticsTool(session, redis, user_id),
            CorrelateTool(session, redis, user_id),
            SearchDocsTool(session, user_id),
            CreatePlanTool(),
        ]

        # Load long-term memory (past insights)
        long_term = await LongTermMemory.load(session, user_id)

        # Build system prompt with user context
        system_prompt = build_health_coach_prompt(user, long_term)

        # Create agent
        return cls(llm_client, tools, system_prompt, memory)
```

### The System Prompt

```
You are a friendly and knowledgeable AI Health Coach for {user.full_name}.
Your role is to help them understand their health habits and improve.

RULES:
- Always base answers on the user's ACTUAL data (use tools to fetch it)
- Never make up data or statistics
- Be encouraging but honest
- Give specific, actionable suggestions
- Reference their uploaded documents when relevant
- Keep responses concise (2-4 paragraphs)

PAST CONTEXT:
{long_term_memory_summary}

You have access to these tools: [tool descriptions]
```

---

<a name="file-list"></a>
## 6. File List & Sub-Part Roadmap

### Agent Layer File Structure

```
backend/app/modules/ai/agents/
├── __init__.py
├── base_agent.py          ← ★★★ ReAct loop implementation
├── health_coach.py        ← Pre-configured health agent
├── memory/
│   ├── __init__.py
│   ├── short_term.py      ← Conversation memory (in-memory)
│   └── long_term.py       ← Past insights memory (PostgreSQL)
└── tools/
    ├── __init__.py
    ├── base_tool.py        ← Abstract tool interface
    ├── query_logs.py       ← Fetch habit log data
    ├── get_analytics.py    ← Get analytics (streaks, weekly, etc.)
    ├── correlate.py        ← Find habit correlations
    ├── search_docs.py      ← RAG vector search
    └── create_plan.py      ← Generate action plans
```

### Sub-Part Roadmap

| Part | Document | Files | Key Concept |
|------|----------|-------|------------|
| **10a** | [Agent Tools](./phase4-part10a-ai-agent-tools.md) | base_tool.py + 5 tool implementations | Abstract tool interface, tool-as-function |
| **10b** | [Agent Memory](./phase4-part10b-ai-agent-memory.md) | short_term.py + long_term.py | Conversation context, persistent insights |
| **10c** | [ReAct Loop ★★★](./phase4-part10c-ai-agent-react-loop.md) | base_agent.py + health_coach.py | THE core agent loop — Think/Act/Observe |
| **10d** | [Agent Connections & Flows](./phase4-part10d-ai-agent-connections-and-flows.md) | Flow diagrams | Full agent trace, error handling |

---

<a name="architecture"></a>
## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT ARCHITECTURE                           │
│                                                                   │
│  User: "Why is my mood low?"                                     │
│    │                                                              │
│    ▼                                                              │
│  ┌─── HealthCoachAgent ─────────────────────────────────────────┐│
│  │                                                               ││
│  │  system_prompt: "You are a health coach for Shreya..."       ││
│  │  tools: [query_logs, get_analytics, correlate, search, plan] ││
│  │  memory: ShortTermMemory + LongTermMemory                    ││
│  │                                                               ││
│  │  ┌─── BaseAgent (ReAct Loop) ───────────────────────────────┐││
│  │  │                                                           │││
│  │  │  1. Build messages (system + memory + user message)       │││
│  │  │  2. LLM.chat(messages, tools=tool_schemas)                │││
│  │  │  3. Response has tool_calls?                              │││
│  │  │     YES → execute tool → add result → goto 2             │││
│  │  │     NO  → return response.content (final answer)          │││
│  │  │  4. Max 5 iterations (safety)                             │││
│  │  │                                                           │││
│  │  └─────────┬─────────────────────────┬──────────────────────┘││
│  │            │ LLM calls               │ tool calls             ││
│  │            ▼                          ▼                        ││
│  │  ┌──────────────┐    ┌──────────────────────────────────────┐││
│  │  │  LLM Layer   │    │  TOOLS                                │││
│  │  │  (Part 08)   │    │  ┌──────────┐ ┌──────────┐          │││
│  │  │  Strategy:   │    │  │query_logs│ │get_analy.│          │││
│  │  │  Ollama/Groq │    │  └──────────┘ └──────────┘          │││
│  │  │  /OpenAI     │    │  ┌──────────┐ ┌──────────┐          │││
│  │  │              │    │  │correlate │ │search_   │          │││
│  │  │              │    │  └──────────┘ │docs      │          │││
│  │  │              │    │               └──────────┘          │││
│  │  │              │    │  ┌──────────────────────┐           │││
│  │  │              │    │  │create_plan           │           │││
│  │  │              │    │  └──────────────────────┘           │││
│  │  └──────────────┘    └──────────────────────────────────────┘││
│  └───────────────────────────────────────────────────────────────┘│
│                                                                   │
│  Data sources:                                                    │
│  ├── PostgreSQL: habits, habit_logs, ai_insights, documents       │
│  ├── Redis: analytics cache                                       │
│  └── pgvector: document chunk embeddings                          │
└─────────────────────────────────────────────────────────────────┘
```

---

<a name="design-decisions"></a>
## 8. Design Decisions

### Decision 1: ReAct Pattern vs OpenAI Function Calling

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Agent Architecture                                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: ReAct (Reason + Act) pattern with tool descriptions        │
│                                                                     │
│  WHY:                                                               │
│  • Provider-agnostic — works with Ollama, Groq, AND OpenAI         │
│  • Transparent reasoning — we see the agent's "thought" process     │
│  • Educational — shows HOW agents work internally                   │
│  • Debuggable — each Think/Act/Observe step is logged              │
│  • Industry-standard — this IS how LangChain/CrewAI work           │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. OpenAI Function Calling (native)                                │
│     ⚠️ Only works with OpenAI — not portable to Ollama/Groq        │
│     ⚠️ Hides reasoning — you only see tool calls, not thoughts     │
│  2. LangChain agents                                                │
│     ⚠️ Heavy dependency, hides the agent loop implementation       │
│  3. No agent (direct LLM + manual tool calls)                       │
│     ❌ The HUMAN decides which tools to call — not intelligent      │
│                                                                     │
│  HOW IT WORKS:                                                      │
│  The LLM sees tool descriptions in its prompt and outputs           │
│  structured "TOOL_CALL: {...}" text. We parse this output,          │
│  execute the tool, and feed the result back as a new message.       │
│  The loop continues until the LLM outputs a final answer            │
│  (no tool call) or hits the 5-iteration limit.                      │
│                                                                     │
│  INTERVIEW TIP: "We implemented the ReAct pattern because it's     │
│  provider-agnostic. The same agent loop works with Ollama, Groq,   │
│  and OpenAI. The LLM sees tool descriptions in its system prompt    │
│  and outputs structured tool calls. We parse, execute, and feed     │
│  results back. Maximum 5 iterations prevents infinite loops."       │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: 5-Tool Maximum

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Agent Tool Set                                    │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: 5 carefully selected tools — not more, not fewer           │
│                                                                     │
│  WHY 5, NOT 10+:                                                    │
│  • More tools = more tokens in the system prompt = more cost        │
│  • More tools = LLM gets confused about which to use               │
│  • 5 tools cover all user needs: data, analytics, correlations,     │
│    documents, and planning                                          │
│                                                                     │
│  WHY THESE 5:                                                       │
│  1. query_logs — "What did I do?" (raw data access)                │
│  2. get_analytics — "How am I doing?" (computed insights)          │
│  3. correlate — "What affects what?" (pattern discovery)            │
│  4. search_docs — "What does my guide say?" (knowledge base)       │
│  5. create_plan — "What should I do?" (action items)               │
│                                                                     │
│  These map to the 5 questions users ask about their health:         │
│  What → How → Why → What else → What next                          │
│                                                                     │
│  INTERVIEW TIP: "We limited the agent to 5 tools to balance        │
│  capability with prompt size and LLM decision quality. More tools   │
│  means more confusion. Our 5 tools cover the full user journey:     │
│  raw data, computed analytics, pattern discovery, document search,  │
│  and action planning."                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: What is a ReAct agent and how does it work?
**A:** "ReAct stands for Reason + Act. It's a loop: the LLM thinks about what to do (reason), calls a tool to get data (act), observes the result, and then either reasons again or gives a final answer. Each iteration is a separate LLM call. We cap at 5 iterations to prevent infinite loops. The LLM sees tool descriptions in its system prompt and outputs structured tool calls that we parse and execute. This is provider-agnostic — the same loop works with Ollama, Groq, and OpenAI."

### Q2: How is an agent different from a chatbot?
**A:** "A chatbot is one LLM call — the user sends a message, the LLM generates a response from its training data. An agent is multiple LLM calls with tool use between them. The agent decides which tools to call based on the question, executes them to get real data, and formulates a response grounded in actual user data. Our chatbot would say 'adults need 7-9 hours of sleep.' Our agent says 'YOUR sleep averaged 6.8 hours this week, down from 7.2 last week, and it correlates with your mood at r=0.72.'"

### Q3: Why did you build the agent from scratch instead of using LangChain?
**A:** "Learning. The ReAct loop is ~100 lines of Python — it's not complex, but it IS important to understand. LangChain wraps this in abstractions that hide the mechanics. By building it ourselves, I can explain exactly how tool calling works: the LLM sees tool descriptions in the prompt, outputs a structured call, we parse it, execute it, and feed the result back. This knowledge transfers to debugging any agent framework."

### Q4: How does agent memory work?
**A:** "Two types. Short-term memory stores the current conversation messages — so the agent knows what was discussed 3 messages ago. It's in-memory and lost when the session ends. Long-term memory stores past insights and recommendations in PostgreSQL — so the agent can say 'last week I suggested you reduce screen time. How did that go?' Long-term memory is loaded at the start of each chat session and injected into the system prompt as context."

### Q5: What are the 5 tools and why those specifically?
**A:** "They map to the 5 questions users ask: (1) query_logs — 'What did I do?' (raw data), (2) get_analytics — 'How am I doing?' (streaks, averages), (3) correlate — 'What affects what?' (pattern discovery), (4) search_docs — 'What does my guide say?' (RAG document search), (5) create_plan — 'What should I do?' (action items). We limited to 5 because more tools increase prompt size and confuse the LLM's tool selection."

### Q6: How do you prevent the agent from looping forever?
**A:** "Three safeguards. First, a hard cap of 5 tool call iterations — after 5, the agent gives its best answer with whatever data it has. Second, the system prompt instructs the LLM to 'answer when you have enough information — don't keep searching.' Third, if a tool call fails, the agent logs the error and continues reasoning with what it has instead of retrying infinitely."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 09c: RAG Connections & Flows](./phase4-part09c-ai-rag-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 10a: Agent Tools](./phase4-part10a-ai-agent-tools.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Agent Sub-Parts

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 10a | [Agent Tools](./phase4-part10a-ai-agent-tools.md) | base_tool.py + 5 tool implementations |
| 10b | [Agent Memory](./phase4-part10b-ai-agent-memory.md) | short_term.py + long_term.py |
| 10c | [ReAct Loop ★★★](./phase4-part10c-ai-agent-react-loop.md) | base_agent.py + health_coach.py |
| 10d | [Agent Connections & Flows](./phase4-part10d-ai-agent-connections-and-flows.md) | Full agent trace diagrams |

---

**End of Phase 4 Part 10: AI Agents Overview**

*The agent is where AI becomes truly powerful. It doesn't just talk — it THINKS, queries your data, finds patterns, searches your documents, and creates plans. The ReAct loop is the beating heart of modern AI applications. Next: the 5 tools that give the agent its capabilities.*
