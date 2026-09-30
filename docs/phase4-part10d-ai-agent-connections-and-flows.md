# 🔄 Phase 4 Part 10d: AI Agent — Connections & Flows

> **"The Agent ties everything together: LLM for reasoning, Tools for data, Memory for context, RAG for documents. This doc traces every interaction."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part10c-ai-agent-react-loop.md](./phase4-part10c-ai-agent-react-loop.md) |
| **Next** | [phase4-part11-ai-workflows-overview.md](./phase4-part11-ai-workflows-overview.md) |
| **Files in This Doc** | 0 (architecture diagrams only) |

---

## 1. Agent Module — Complete File Map

```
backend/app/modules/ai/agents/
├── base_agent.py      ─── Part 10c ── ★★★ ReAct loop (~100 lines)
├── health_coach.py    ─── Part 10c ── Pre-configured health agent
├── tools/
│   ├── base_tool.py   ─── Part 10a ── Abstract tool interface
│   ├── query_logs.py  ─── Part 10a ── Fetch habit data from DB
│   ├── get_analytics.py ─ Part 10a ── Get cached analytics
│   ├── correlate.py   ─── Part 10a ── Find habit correlations
│   ├── search_docs.py ─── Part 10a ── RAG vector search (Part 09)
│   └── create_plan.py ─── Part 10a ── LLM-generated action plan
└── memory/
    ├── short_term.py  ─── Part 10b ── Conversation buffer (20 messages)
    └── long_term.py   ─── Part 10b ── Persistent insights (Redis hash)
```

---

## 2. Full Agent Trace — "Why is my mood low?"

```
USER: "Why is my mood low this week?"
  │
  ▼
HealthCoachAgent.create(session, redis, user_id, user)
  ├── Load long-term memory: "KNOWN FACTS: wants better sleep, runs 3x/week"
  ├── Create 5 tools: query_logs, get_analytics, correlate, search_docs, create_plan
  ├── Build system prompt: health coach persona + tools + known facts
  └── Create BaseAgent(llm, tools, system_prompt, ShortTermMemory())

agent.run("Why is my mood low this week?")
  │
  ├── short_term.add_user_message("Why is my mood low?")
  ├── messages = [system_prompt(~300 tokens), user_msg(~10 tokens)]
  │
  ▼ ITERATION 1
  llm.chat(messages, tools=5_schemas, temperature=0.3)
    → LLM: "I need mood data" → ToolCall(query_logs, {habit:"Mood", days:7})
    → Execute: QueryLogsTool → LogRepository → habit_logs table
    → Result: "Mood: Sep20=8, Sep21=7, Sep22=5, Sep23=4, Sep24=5, Sep25=6, Sep26=5"
    → messages += [assistant, tool_result] → now 4 messages

  ▼ ITERATION 2
  llm.chat(messages, tools=5_schemas)
    → LLM: "What correlates?" → ToolCall(correlate, {days:30})
    → Execute: CorrelateTool → AnalyticsService → Pearson calculation
    → Result: "Sleep↔Mood r=0.72 strong+, Exercise↔Mood r=0.45 moderate+"
    → messages += [assistant, tool_result] → now 6 messages

  ▼ ITERATION 3
  llm.chat(messages, tools=5_schemas)
    → LLM: "Check sleep data" → ToolCall(query_logs, {habit:"Sleep", days:7})
    → Execute: QueryLogsTool → LogRepository
    → Result: "Sleep: Sep20=7.5h, Sep21=7.0h, Sep22=5.0h...avg 5.8h"
    → messages += [assistant, tool_result] → now 8 messages

  ▼ ITERATION 4
  llm.chat(messages, tools=5_schemas)
    → LLM: "I have enough info" → content="Your mood dropped because..."
    → NO tool calls → FINAL ANSWER
    → short_term.add_assistant_message(answer)
    → Return answer

RESULT: 4 iterations, 3 tool calls, ~3500 tokens
  "Your mood averaged 5.7 this week (down from 7.2). This strongly
   correlates with your sleep decline (r=0.72). Sleep dropped from
   7.5h to 5.0h mid-week. On days you sleep 7+ hours, mood averages
   7.5. Suggestion: prioritize 7+ hours tonight."
```

---

## 3. How Agent Connects to All Other AI Layers

```
┌──────────────────────────────────────────────────────────────────┐
│                   AI MODULE — COMPLETE ARCHITECTURE               │
│                                                                    │
│  ┌─── AGENT (Part 10) ──────────────────────────────────────────┐│
│  │  HealthCoachAgent                                              ││
│  │    ├── BaseAgent (ReAct loop)                                  ││
│  │    ├── 5 Tools:                                                ││
│  │    │   ├── query_logs → LogRepository (Part 06)               ││
│  │    │   ├── get_analytics → AnalyticsService+Cache (Part 07)   ││
│  │    │   ├── correlate → AnalyticsService (Part 07)             ││
│  │    │   ├── search_docs → Retriever → pgvector (Part 09)       ││
│  │    │   └── create_plan → LLM (Part 08)                        ││
│  │    ├── Short-term memory (conversation)                        ││
│  │    └── Long-term memory (Redis insights)                       ││
│  └───────────────────────────────┬───────────────────────────────┘│
│                                  │ uses                           │
│                                  ▼                                │
│  ┌─── LLM (Part 08) ───┐  ┌─── RAG (Part 09) ──────────────┐   │
│  │ Strategy: Ollama/    │  │ embed query → pgvector search   │   │
│  │ Groq/OpenAI          │  │ → format context + citations    │   │
│  │ chat() + stream()    │  └──────────────────────────────────┘   │
│  └──────────────────────┘                                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent Module Summary

| Metric | Value |
|--------|-------|
| Python files | 10 (base_agent, health_coach, 5 tools, 2 memory, base_tool) |
| Tool count | 5 (query_logs, get_analytics, correlate, search_docs, create_plan) |
| Max iterations | 5 per question |
| Memory types | 2 (short-term: 20 msgs, long-term: 20 insights) |
| Temperature | 0.3 (precise reasoning) |
| LLM calls per question | 2-5 typical |

### AI Module — All Sub-Modules Complete ✅

| Layer | Parts | Status |
|-------|-------|--------|
| LLM | 08a-08c | ✅ Strategy pattern, 3 providers, prompts, tokens |
| RAG | 09a-09c | ✅ Ingestion pipeline, pgvector search, retrieval |
| Agents | 10a-10d | ✅ 5 tools, memory, ReAct loop, flows |

---

## 5. Navigation

| ⬅️ Previous | [Part 10c: ReAct Loop ★★★](./phase4-part10c-ai-agent-react-loop.md) |
| ➡️ Next | [Part 11: AI Workflows Overview](./phase4-part11-ai-workflows-overview.md) |

**🎉 The Agent layer is COMPLETE.** Next: Workflows (weekly report) and the AI service/router.
