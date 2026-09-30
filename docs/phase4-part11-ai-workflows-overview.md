# ⚙️ Phase 4 Part 11: AI — Agentic Workflows Overview & Roadmap

> **"A single agent answers one question. A workflow orchestrates MULTIPLE agents — each specializing in one task — to produce something no single agent could: a personalized, data-driven, beautifully written weekly health report. This is how CrewAI, AutoGen, and LangGraph work."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 11 (AI Module — Agentic Workflows Overview) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.4 — Weekly Reports & Agentic Workflows |
| **Previous** | [phase4-part10d-ai-agent-connections-and-flows.md](./phase4-part10d-ai-agent-connections-and-flows.md) |
| **Next** | [phase4-part11a-ai-workflow-pipeline.md](./phase4-part11a-ai-workflow-pipeline.md) |
| **Module Files** | 6 files (base_workflow.py, orchestrator.py, data_collector.py, analyzer.py, report_writer.py, __init__.py) |
| **Sub-Parts** | 2 documents (11a pipeline, 11b flows) |
| **Difficulty** | Hard (pipeline pattern, checkpoint state, retry logic, multi-LLM orchestration) |

---

## 📖 Table of Contents

1. [What Is an Agentic Workflow?](#what-is-workflow)
2. [Single Agent vs Workflow — Why Both?](#agent-vs-workflow)
3. [The Weekly Report Workflow — Our Implementation](#weekly-report)
4. [File List & Build Order](#file-list)
5. [Sub-Part Roadmap](#roadmap)
6. [Architecture Diagram](#architecture)
7. [Key Concepts You'll Learn](#concepts)
8. [Design Decisions](#design-decisions)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="what-is-workflow"></a>
## 1. What Is an Agentic Workflow?

An **agentic workflow** is a pipeline of AI-powered steps that execute in sequence. Each step specializes in one task and passes its output to the next step.

### Real-World Analogy

Think of a **newspaper article production**:
- **Step 1 (Reporter):** Gathers facts, interviews sources, collects data
- **Step 2 (Analyst):** Reviews the facts, identifies the key story angle, draws conclusions
- **Step 3 (Writer):** Takes the facts + analysis and writes an engaging article
- **Step 4 (Editor):** Reviews, formats, publishes

No single person does all four jobs well. Each specialist produces better output than a generalist doing everything. Same principle applies to AI workflows.

### How This Differs from a Single Agent

```
SINGLE AGENT (Part 10):
  User: "Generate my weekly report"
  Agent: [one LLM call] → tries to gather data, analyze, AND write
         → mediocre results (too many tasks in one prompt)

AGENTIC WORKFLOW (this part):
  Step 1: DataCollector → queries DB for habits, logs, streaks, weekly comparison
         → produces structured data summary (NO LLM call — pure DB)
  Step 2: Analyzer → LLM reads the data → identifies patterns, concerns, wins
         → produces structured analysis (one focused LLM call)
  Step 3: ReportWriter → LLM reads data + analysis → writes friendly report
         → produces polished markdown (one focused LLM call)

  Three specialized steps > one do-everything prompt
```

---

<a name="agent-vs-workflow"></a>
## 2. Single Agent vs Workflow — Why Both?

| Feature | Single Agent (Part 10) | Workflow (Part 11) |
|---------|----------------------|-------------------|
| **Trigger** | User chat message | Scheduled (Lambda) or on-demand (API) |
| **Interaction** | Interactive — user asks follow-ups | Non-interactive — runs autonomously |
| **LLM calls** | 1–5 (dynamic, based on question) | 2–3 (fixed pipeline) |
| **Tool use** | Yes (5 tools, ReAct loop) | No tools — data fetched in step 1 |
| **Output** | Conversational response | Structured document (markdown report) |
| **State** | Short-term memory (conversation) | Step-to-step data passing |
| **Error handling** | Continue reasoning with partial data | Retry failed steps, graceful degradation |
| **Use case** | "How's my sleep?" (interactive Q&A) | Weekly report, insight generation (batch) |

**Why BOTH?** The agent handles real-time chat. The workflow handles batch tasks that need multiple specialized AI steps. Different problems, different solutions.

---

<a name="weekly-report"></a>
## 3. The Weekly Report Workflow — Our Implementation

The weekly report is the primary workflow. It generates a personalized AI report every Sunday:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  WEEKLY REPORT WORKFLOW — 3 Steps                                        │
│                                                                          │
│  ┌─── Step 1: DATA COLLECTOR (No LLM) ─────────────────────────────────┐│
│  │  Queries:                                                             ││
│  │  ├── HabitRepository → 6 active habits (names, types, targets)       ││
│  │  ├── LogRepository → 7 days of logs (~42 entries)                    ││
│  │  ├── AnalyticsRepository → streaks for all habits                    ││
│  │  ├── AnalyticsRepository → weekly summary (this vs last week)        ││
│  │  └── AnalyticsRepository → completion rates                          ││
│  │                                                                       ││
│  │  Output: structured text summary (~1500 tokens)                       ││
│  │  "ACTIVE HABITS (6): Water (numeric, target 8 glasses)...            ││
│  │   THIS WEEK'S LOGS: Sep 20 | Water: 7 glasses | Sleep: 7.5 hours... ││
│  │   STREAKS: Water 15 days (best: 30)...                               ││
│  │   THIS WEEK vs LAST: Water 7.4 vs 7.0 (+5.7%)..."                   ││
│  │  Time: ~100ms (pure DB queries)                                       ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                              │ passes data_summary to next step           │
│                              ▼                                            │
│  ┌─── Step 2: ANALYZER (1 LLM call) ───────────────────────────────────┐│
│  │  Prompt: WEEKLY_REPORT_ANALYSIS template                              ││
│  │  "Analyze this data. Identify improvements, concerns, correlations.   ││
│  │   Provide 2-3 specific recommendations."                              ││
│  │                                                                       ││
│  │  LLM output:                                                          ││
│  │  "## Highlights                                                       ││
│  │   - Water streak hit 15 days — best consistency this month           ││
│  │   - Exercise completion improved from 60% to 80%                     ││
│  │   ## Areas to Watch                                                   ││
│  │   - Sleep declined 5.6% (7.2h → 6.8h avg)                           ││
│  │   - Mood correlates with sleep (r=0.72) — both declining             ││
│  │   ## Recommendations                                                  ││
│  │   - Set a 10 PM bedtime alarm to reclaim 30 minutes of sleep        ││
│  │   - Try a 20-minute walk before dinner (exercise boosts sleep)"      ││
│  │                                                                       ││
│  │  Temperature: 0.4 (factual analysis, slight creativity)               ││
│  │  Tokens: ~800 input + ~500 output = ~1300                            ││
│  │  Time: ~2-5s                                                          ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                              │ passes analysis to next step               │
│                              ▼                                            │
│  ┌─── Step 3: REPORT WRITER (1 LLM call) ──────────────────────────────┐│
│  │  Prompt: WEEKLY_REPORT_WRITER template                                ││
│  │  Input: data_summary (step 1) + analysis (step 2)                    ││
│  │  "Write a friendly, personalized weekly report for Shreya.            ││
│  │   Include greeting, key stats, analysis insights, motivating close."  ││
│  │                                                                       ││
│  │  LLM output:                                                          ││
│  │  "# 📊 Weekly Health Report — Sep 20-26                              ││
│  │                                                                       ││
│  │   Hi Shreya! 🎉 Great week for water — 15 days straight!            ││
│  │                                                                       ││
│  │   **This Week's Highlights:**                                         ││
│  │   - 💧 Water: 7.4 glasses/day (target: 8) — 15-day streak!         ││
│  │   - 🏃 Exercise: 80% completion (up from 60% last week!)            ││
│  │   - 😊 Mood: averaged 6.8/10                                        ││
│  │                                                                       ││
│  │   **Worth Watching:**                                                 ││
│  │   Your sleep dipped to 6.8 hours (from 7.2 last week). Since your   ││
│  │   mood strongly correlates with sleep (we see this in your data),    ││
│  │   getting back to 7+ hours could boost both.                         ││
│  │                                                                       ││
│  │   **Next Week's Focus:**                                              ││
│  │   Try setting a 10 PM bedtime alarm. On days you exercise, you      ││
│  │   sleep 45 minutes more — so keep that exercise streak going! 💪"   ││
│  │                                                                       ││
│  │  Temperature: 0.6 (more creative for engaging writing)                ││
│  │  Tokens: ~2000 input + ~800 output = ~2800                           ││
│  │  Time: ~3-8s                                                          ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                              │                                            │
│                              ▼                                            │
│  Save to ai_insights table (type="weekly_report")                        │
│  Optionally send notification email to user                              │
│                                                                          │
│  TOTAL: 2 LLM calls, ~4100 tokens, ~5-15 seconds                        │
└──────────────────────────────────────────────────────────────────────────┘
```

---

<a name="file-list"></a>
## 4. File List & Build Order

### Workflow Layer File Structure

```
backend/app/modules/ai/workflows/
├── __init__.py
├── base_workflow.py           ← Abstract workflow interface + data classes
├── orchestrator.py            ← Runs workflows with retry + logging
└── weekly_report/
    ├── __init__.py
    ├── data_collector.py      ← Step 1: fetch all data from DB
    ├── analyzer.py            ← Step 2: LLM analyzes patterns
    └── report_writer.py       ← Step 3: LLM writes friendly report
```

### Build Order

| # | File | Why This Order |
|---|------|---------------|
| 1 | `base_workflow.py` | Defines StepResult, WorkflowResult, BaseWorkflow — everything else uses these |
| 2 | `orchestrator.py` | Runs any workflow — depends only on base_workflow |
| 3 | `data_collector.py` | Step 1: no LLM, just DB queries |
| 4 | `analyzer.py` | Step 2: uses LLM + prompt template |
| 5 | `report_writer.py` | Step 3: uses LLM + prompt template + data from steps 1-2 |

---

<a name="roadmap"></a>
## 5. Sub-Part Roadmap

### Part 11a: Workflow Pipeline Implementation

```
📄 phase4-part11a-ai-workflow-pipeline.md
├── base_workflow.py   — StepResult + WorkflowResult dataclasses, BaseWorkflow ABC
├── orchestrator.py    — Step-by-step execution, retry logic, error recovery
├── data_collector.py  — Step 1: 5 DB queries → structured text summary
├── analyzer.py        — Step 2: LLM analysis with WEEKLY_REPORT_ANALYSIS template
└── report_writer.py   — Step 3: LLM writing with WEEKLY_REPORT_WRITER template

KEY CONCEPTS: Pipeline pattern, step data passing, retry with backoff, graceful degradation
TIME: ~60 minutes
```

### Part 11b: Workflow Connections & Flows

```
📄 phase4-part11b-ai-workflow-connections-and-flows.md
├── Full step-by-step execution trace (with real data examples)
├── Retry scenario: Step 2 fails → retry → succeeds
├── Graceful degradation: Step 3 fails → partial report saved
├── Scheduling: Lambda trigger (Sunday 10 PM) + on-demand (POST /ai/weekly-report)
└── Module summary with token costs and timing

TIME: ~20 minutes
```

---

<a name="architecture"></a>
## 6. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW LAYER                                        │
│                                                                          │
│  TRIGGER:                                                                │
│  ├── Lambda (Sunday 10 PM UTC) → for each active user                   │
│  └── POST /ai/weekly-report → on-demand for one user                    │
│                                                                          │
│  ┌─── WorkflowOrchestrator ─────────────────────────────────────────┐   │
│  │  For each step in workflow.steps:                                  │   │
│  │    1. Execute step (with retry, max 2 attempts)                   │   │
│  │    2. Log timing + token count                                     │   │
│  │    3. Pass output to next step                                     │   │
│  │    4. If failed after retries → continue with partial data         │   │
│  │  Return: WorkflowResult (all steps + final output + total tokens)  │   │
│  └───────────────────────────┬───────────────────────────────────────┘   │
│                              │ runs                                       │
│                              ▼                                            │
│  ┌─── WeeklyReportWorkflow ──────────────────────────────────────────┐   │
│  │  steps = ["collect", "analyze", "write"]                           │   │
│  │                                                                    │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │   │
│  │  │ DataCollector   │→│ Analyzer        │→│ ReportWriter    │      │   │
│  │  │ (DB queries)    │  │ (LLM analysis)  │  │ (LLM writing)  │      │   │
│  │  │ 5 repo calls    │  │ temp=0.4        │  │ temp=0.6        │      │   │
│  │  │ ~100ms          │  │ ~2-5s           │  │ ~3-8s           │      │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘      │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Data sources:                                                           │
│  ├── HabitRepository, LogRepository, AnalyticsRepository (Step 1)        │
│  ├── LLM via BaseLLMClient + prompt_templates (Steps 2-3)              │
│  └── ai_insights table (save final report)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

<a name="concepts"></a>
## 7. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **Pipeline Pattern** | Steps execute in sequence, each receives previous output | Orchestrator |
| 2 | **StepResult dataclass** | Each step returns: success, data, error, tokens, duration | base_workflow.py |
| 3 | **WorkflowResult** | Final result: all step results + total tokens + timing | base_workflow.py |
| 4 | **Retry with fallback** | Failed step → retry → if still fails → continue with partial data | orchestrator.py |
| 5 | **Graceful degradation** | Partial report is better than no report | orchestrator.py |
| 6 | **Specialized LLM calls** | Analysis (temp=0.4, factual) vs Writing (temp=0.6, creative) | analyzer.py, writer.py |
| 7 | **Two-step LLM** | Separate analysis from writing → better quality than one prompt | Steps 2+3 |
| 8 | **Data collection without LLM** | Step 1 is pure DB queries — fast, reliable, no token cost | data_collector.py |
| 9 | **Template-driven prompts** | Jinja2 templates from Part 08c used in each LLM step | analyzer.py, writer.py |
| 10 | **`time.perf_counter()`** | High-resolution timing for step duration tracking | orchestrator.py |

---

<a name="design-decisions"></a>
## 8. Design Decisions

### Decision 1: Separate Analysis from Writing (Two-Step LLM)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Report Generation Strategy                        │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Two LLM calls — analysis (Step 2) + writing (Step 3)      │
│                                                                     │
│  WHY:                                                               │
│  • One prompt doing both → mediocre quality (task overload)         │
│  • Analysis focuses on WHAT patterns exist (factual, temp=0.4)      │
│  • Writing focuses on HOW to present them (creative, temp=0.6)      │
│  • Like asking a data analyst and a copywriter to collaborate       │
│  • Each prompt is shorter → LLM is more focused → better output    │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. One LLM call (single massive prompt)                            │
│     ❌ Analysis is shallow, writing is generic — too many tasks     │
│  2. Three calls (patterns, recommendations, writing)                │
│     ⚠️ Better quality but 50% more tokens. Diminishing returns.    │
│  3. Agent with tools (ReAct loop)                                   │
│     ❌ Overkill — we know the exact steps in advance. No need for  │
│        the agent to "decide" what to do.                            │
│                                                                     │
│  COST: 2 LLM calls × ~2000 tokens = ~4000 tokens per report        │
│  With Ollama/Groq: $0. With OpenAI GPT-4o: ~$0.04 per report.      │
│                                                                     │
│  INTERVIEW TIP: "We split the weekly report into analysis and       │
│  writing LLM calls. The analyst prompt uses temperature 0.4 for     │
│  factual pattern detection. The writer prompt uses 0.6 for engaging  │
│  prose. This separation consistently produces higher quality than    │
│  a single do-everything prompt."                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Workflow vs Agent for Reports

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Workflow vs Agent for Weekly Reports               │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Workflow (fixed pipeline) — not agent (dynamic ReAct)       │
│                                                                     │
│  WHY:                                                               │
│  • We know the EXACT steps: collect → analyze → write               │
│  • No decisions needed — an agent would just call the same tools    │
│    in the same order every time                                     │
│  • Pipeline is deterministic: same input → same output quality      │
│  • Retry is simpler: retry a failed step, not re-run a reasoning    │
│    loop                                                             │
│                                                                     │
│  WHEN TO USE EACH:                                                  │
│  Agent:    Unknown steps. "Why is my mood low?" → agent decides     │
│            which tools to call based on the question.               │
│  Workflow: Known steps. Weekly report always needs data → analysis   │
│            → writing. No decision-making needed.                    │
│                                                                     │
│  REAL-WORLD PARALLEL:                                               │
│  Agent = a developer debugging a bug (unknown path, uses tools)     │
│  Workflow = a CI/CD pipeline (fixed: lint → test → build → deploy)  │
│                                                                     │
│  INTERVIEW TIP: "We use agents for interactive Q&A (unknown steps)  │
│  and workflows for batch tasks (known steps). The weekly report     │
│  always follows: collect data → analyze patterns → write report.    │
│  An agent would just follow the same steps without adding value."   │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 3: Retry + Graceful Degradation

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Error Handling Strategy                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Retry failed steps (max 2 attempts) + continue on failure  │
│                                                                     │
│  WHY:                                                               │
│  • LLM calls have transient failures (timeout, rate limit, 500)     │
│  • One retry usually succeeds (transient errors are rare + short)   │
│  • If step 2 fails permanently → save raw data (step 1 output) as  │
│    the report. A partial report beats no report.                    │
│  • Never crash the workflow — always produce SOMETHING              │
│                                                                     │
│  ERROR SCENARIOS:                                                   │
│  Step 1 fails: no data → can't continue → workflow fails with       │
│    helpful error ("No data available for this week")                │
│  Step 2 fails: data exists but no analysis → Step 3 writes report   │
│    from raw data only (less insightful but still useful)            │
│  Step 3 fails: data + analysis exist → save analysis as the report  │
│    (structured but not prose — still valuable)                      │
│                                                                     │
│  INTERVIEW TIP: "We retry failed steps once (transient LLM errors)  │
│  and continue on permanent failure. A partial report — data without │
│  analysis, or analysis without prose — is better than no report.    │
│  This is graceful degradation."                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: What is an agentic workflow and how is it different from a single agent?
**A:** "A single agent is a ReAct loop — it reasons about what to do, calls tools, observes results, and iterates. The steps are dynamic. An agentic workflow is a fixed pipeline of specialized AI steps — each step focuses on one task and passes output to the next. Our weekly report uses 3 steps: data collection (DB queries, no LLM), analysis (LLM identifies patterns), and writing (LLM writes a friendly report). This is like CrewAI's crew of agents or LangGraph's stateful workflows. We use agents for interactive chat (unknown steps) and workflows for batch tasks (known steps)."

### Q2: Why separate data collection from the LLM steps?
**A:** "Step 1 is pure database queries — no LLM call, no token cost, and guaranteed reliability. It fetches habits, logs, streaks, weekly comparison, and completion rates. This takes ~100ms and produces a structured text summary. The LLM steps (2 and 3) receive this pre-formatted data. If we let the LLM fetch data itself (like the agent does), it would need multiple tool calls and might miss important data points. Pre-collecting ensures complete, consistent data input."

### Q3: How does the orchestrator handle failures?
**A:** "The orchestrator retries failed steps up to twice. LLM calls have transient failures — timeouts, rate limits, server errors — that usually succeed on retry. If a step fails permanently after all retries, the orchestrator continues with the remaining steps using partial data. A report with data but no analysis is still useful. A report with analysis but no polished writing is still readable. We never crash the entire workflow because one step failed."

### Q4: Why temperature 0.4 for analysis and 0.6 for writing?
**A:** "Temperature controls LLM randomness. Analysis needs to be factual and consistent — 'sleep declined 5.6%' should be the same every time. Temperature 0.4 keeps the output focused. Writing needs personality and engagement — 'Hi Shreya! 🎉 Great week for water!' benefits from slight creativity. Temperature 0.6 makes the prose more natural and varied. Using 0.7+ would make the writing too unpredictable; 0.3 or lower would make it robotic."

### Q5: How does this relate to tools like CrewAI and LangGraph?
**A:** "Same concepts, different implementations. CrewAI assigns roles to agents (researcher, analyst, writer) — our DataCollector, Analyzer, and ReportWriter are equivalent. LangGraph uses a state machine to route between nodes — our orchestrator runs steps sequentially. AutoGen uses multi-agent conversations — our steps pass data forward instead of conversing. We built from scratch to understand the pattern. In production, we'd evaluate CrewAI or LangGraph for their ecosystems."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 10d: Agent Connections & Flows](./phase4-part10d-ai-agent-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 11a: Workflow Pipeline Implementation](./phase4-part11a-ai-workflow-pipeline.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Workflow Sub-Parts

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 11a | [Workflow Pipeline](./phase4-part11a-ai-workflow-pipeline.md) | base_workflow.py + orchestrator.py + 3 weekly_report step files (full source) |
| 11b | [Workflow Connections & Flows](./phase4-part11b-ai-workflow-connections-and-flows.md) | Execution trace, retry scenario, scheduling, module summary |

---

**End of Phase 4 Part 11: Agentic Workflows Overview**

*Workflows orchestrate specialized AI steps into something no single agent could produce. Next: the full source code for all 6 files — base workflow, orchestrator, and the 3-step weekly report pipeline.*
