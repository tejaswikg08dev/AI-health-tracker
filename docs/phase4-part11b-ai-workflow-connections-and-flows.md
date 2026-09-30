# 🔄 Phase 4 Part 11b: AI Workflow — Connections & Flows

> **"Three flows tell the full story: the happy path (everything works), the retry path (step 2 fails once then succeeds), and the degradation path (step 3 fails permanently — we save what we have). Understanding all three means understanding production AI systems."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 11b (Workflow Flows & Architecture) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.4 — Weekly Reports & Agentic Workflows |
| **Previous** | [phase4-part11a-ai-workflow-pipeline.md](./phase4-part11a-ai-workflow-pipeline.md) |
| **Next** | [phase4-part12-ai-service-router-overview.md](./phase4-part12-ai-service-router-overview.md) |
| **Files in This Doc** | 0 (architecture diagrams only) |
| **Time to Read** | ~20 minutes |

---

## 📖 Table of Contents

1. [Workflow Module — Complete File Map](#file-map)
2. [Flow 1: Happy Path (All Steps Succeed)](#happy-path)
3. [Flow 2: Retry Path (Step 2 Fails, Then Succeeds)](#retry-path)
4. [Flow 3: Degradation Path (Step 3 Fails Permanently)](#degradation-path)
5. [How the Workflow Gets Triggered](#triggers)
6. [Token Cost Analysis](#costs)
7. [Workflow Module Summary](#summary)
8. [Navigation](#navigation)

---

<a name="file-map"></a>
## 1. Workflow Module — Complete File Map

```
backend/app/modules/ai/workflows/
├── base_workflow.py       ─── Part 11a ── StepResult, WorkflowResult, BaseWorkflow ABC
├── orchestrator.py        ─── Part 11a ── Step runner with retry + graceful degradation
├── weekly_report/
│   ├── __init__.py
│   ├── data_collector.py  ─── Part 11a ── Step 1: 5 DB queries → structured text
│   ├── analyzer.py        ─── Part 11a ── Step 2: LLM analysis (temp=0.4)
│   └── report_writer.py   ─── Part 11a ── Step 3: LLM writing (temp=0.6)
└── __init__.py

Dependency chain:
  orchestrator.py → base_workflow.py (uses StepResult, WorkflowResult, BaseWorkflow)
  WeeklyReportWorkflow → data_collector + analyzer + report_writer
  data_collector → HabitRepo + LogRepo + AnalyticsRepo (cross-module)
  analyzer → BaseLLMClient + WEEKLY_REPORT_ANALYSIS template (Part 08)
  report_writer → BaseLLMClient + WEEKLY_REPORT_WRITER template (Part 08)
```

---

<a name="happy-path"></a>
## 2. Flow 1: Happy Path (All Steps Succeed)

```
TRIGGER: Lambda (Sunday 10 PM UTC) OR POST /ai/weekly-report

STEP  COMPONENT                    ACTION                           TIME
────  ─────────                    ──────                           ────
 1    AI Service                   Creates WeeklyReportWorkflow
                                   Creates WorkflowOrchestrator(max_retries=2)
                                   Calls orchestrator.run(workflow, initial_data=None)

 2    Orchestrator                 workflow.steps = ["collect", "analyze", "write"]
      .run()                       current_data = None
                                   start_time = perf_counter()

══ STEP "collect" ════════════════════════════════════════════════════════
 3    Orchestrator                 _run_step_with_retry(workflow, "collect", None)
      ._run_step_with_retry()      attempt = 1

 4    WeeklyReportWorkflow         execute_step("collect", None)
      .execute_step()                → DataCollector(session, user_id).collect()

 5    DataCollector                5 database queries:
      .collect()                     ├── habit_repo.get_user_habits() → 6 habits
                                     ├── log_repo.get_logs_for_range() → 42 logs (7 days)
                                     ├── analytics_repo.get_streaks() → 6 streak records
                                     ├── analytics_repo.get_weekly_summary() → 6 comparisons
                                     └── analytics_repo.get_completion_rates() → 6 rates

                                   Format into structured text:
                                   "ACTIVE HABITS (6):\n  - Water Intake (numeric)..."
                                   ~1500 tokens of structured data

 6    Orchestrator                 StepResult(success=True, data="ACTIVE HABITS...",   ~0.1s
                                             tokens_used=0, duration=0.1s)
                                   current_data = data_summary
                                   Log: "workflow_step_completed, step=collect, 0.1s"

══ STEP "analyze" ════════════════════════════════════════════════════════
 7    Orchestrator                 _run_step_with_retry(workflow, "analyze", data_summary)
                                   attempt = 1

 8    WeeklyReportWorkflow         execute_step("analyze", data_summary)
                                     → Analyzer(llm).analyze(data_summary)

 9    Analyzer                     Build prompt:
      .analyze()                     system: "You are a health data analyst."
                                     user: WEEKLY_REPORT_ANALYSIS.render(data_summary)

                                   LLM call (temp=0.4, max_tokens=1500):
                                     → Ollama/Groq/OpenAI chat API
                                     → "## Highlights\n- Water streak hit 15 days!\n
                                        - Exercise completion improved 60%→80%\n
                                        ## Areas to Watch\n- Sleep declined 5.6%...\n
                                        ## Recommendations\n- Set 10 PM bedtime alarm..."

10    Orchestrator                 StepResult(success=True, data="## Highlights...",   ~3.5s
                                             tokens_used=1300, duration=3.5s)
                                   current_data = analysis
                                   Log: "workflow_step_completed, step=analyze, 1300 tokens, 3.5s"

══ STEP "write" ══════════════════════════════════════════════════════════
11    Orchestrator                 _run_step_with_retry(workflow, "write", analysis)
                                   attempt = 1

12    WeeklyReportWorkflow         execute_step("write", analysis)
                                     → ReportWriter(llm, "Shreya").write(data_summary, analysis)
                                   NOTE: writer receives BOTH data_summary (step 1) AND
                                         analysis (step 2) — stored in workflow state

13    ReportWriter                 Build prompt:
      .write()                       system: "Friendly health coach. Markdown. Encouraging."
                                     user: WEEKLY_REPORT_WRITER.render(
                                       user_name="Shreya",
                                       data_summary="ACTIVE HABITS (6)...",
                                       analysis="## Highlights\n- Water streak 15 days..."
                                     )

                                   LLM call (temp=0.6, max_tokens=2000):
                                     → "# 📊 Weekly Health Report — Sep 20-26\n\n
                                        Hi Shreya! 🎉 Amazing week for water — 15 days!\n\n
                                        **This Week's Highlights:**\n
                                        - 💧 Water: 7.4 glasses/day — 15-day streak!\n
                                        - 🏃 Exercise: 80% completion (was 60%!)\n\n
                                        **Worth Watching:**\n
                                        Your sleep dipped to 6.8h (from 7.2h). Since mood\n
                                        strongly correlates with sleep in your data...\n\n
                                        **Next Week's Focus:**\n
                                        Try a 10 PM bedtime alarm. On exercise days you\n
                                        sleep 45 minutes more — keep it up! 💪"

14    Orchestrator                 StepResult(success=True, data="# 📊 Weekly...",    ~5.2s
                                             tokens_used=2800, duration=5.2s)
                                   current_data = report_markdown
                                   Log: "workflow_step_completed, step=write, 2800 tokens, 5.2s"

══ WORKFLOW COMPLETE ═════════════════════════════════════════════════════
15    Orchestrator                 WorkflowResult(
                                     workflow_name="weekly_report",
                                     success=True,
                                     steps=[collect_result, analyze_result, write_result],
                                     final_output="# 📊 Weekly Health Report...",
                                     total_tokens=4100,         ← 0 + 1300 + 2800
                                     total_duration_seconds=8.8, ← 0.1 + 3.5 + 5.2
                                   )
                                   Log: "workflow_completed, success=True, 4100 tokens, 8.8s"

16    AI Service                   Save to ai_insights table:
                                     INSERT INTO ai_insights
                                       (user_id, insight_type="weekly_report",
                                        content="# 📊 Weekly Health Report...",
                                        created_at=now())
                                   Optionally send notification email to user
```

---

<a name="retry-path"></a>
## 3. Flow 2: Retry Path (Step 2 Fails, Then Succeeds)

```
Steps 1-6: SAME as happy path (collect succeeds)

══ STEP "analyze" — ATTEMPT 1 ════════════════════════════════════════════
 7    Orchestrator                 _run_step_with_retry("analyze", data_summary)
                                   attempt = 1

 8    Analyzer.analyze()           LLM call → httpx.ConnectTimeout!
                                   (Ollama is busy, Groq rate-limited, network hiccup)

 9    Orchestrator                 EXCEPTION caught:
                                     StepResult(success=False, error="Connection timed out")
                                   Log: "workflow_step_retry, step=analyze, attempt=1, error=timeout"

══ STEP "analyze" — ATTEMPT 2 ════════════════════════════════════════════
10    Orchestrator                 attempt = 2 (retry)

11    Analyzer.analyze()           LLM call → SUCCESS this time
                                   → "## Highlights\n- Water streak 15 days!..."

12    Orchestrator                 StepResult(success=True, data="## Highlights...",
                                             tokens_used=1300)
                                   Return — exit retry loop

══ STEP "write" ══════════════════════════════════════════════════════════
13-16: SAME as happy path (write succeeds on first attempt)

RESULT: WorkflowResult(success=True, total_tokens=4100)
  All 3 steps completed. The user never knows step 2 was retried.
  Orchestrator logs show the retry — ops team can monitor retry rates.
```

### Why Retries Work for LLM Calls

| Failure Type | Cause | Retry Success Rate |
|-------------|-------|-------------------|
| Connection timeout | LLM server busy | ~90% (transient) |
| Rate limit (429) | Too many requests | ~80% (wait and retry) |
| Server error (500) | Provider outage | ~50% (depends on duration) |
| Invalid response | LLM hallucinated bad format | ~60% (non-deterministic) |

Most LLM failures are **transient** — they succeed on the next attempt. This is why `max_retries=2` is effective.

---

<a name="degradation-path"></a>
## 4. Flow 3: Degradation Path (Step 3 Fails Permanently)

```
Steps 1-6:  collect succeeds → data_summary
Steps 7-12: analyze succeeds → analysis (after retry)

══ STEP "write" — ATTEMPT 1 ══════════════════════════════════════════════
13    ReportWriter.write()         LLM call → timeout (Ollama overloaded)

14    Orchestrator                 StepResult(success=False, error="Timeout")
                                   Log: "workflow_step_retry, step=write, attempt=1"

══ STEP "write" — ATTEMPT 2 ══════════════════════════════════════════════
15    ReportWriter.write()         LLM call → ANOTHER timeout (persistent issue)

16    Orchestrator                 StepResult(success=False, error="Timeout")
                                   All retries exhausted — return failure

══ WORKFLOW CONTINUES (graceful degradation) ══════════════════════════════
17    Orchestrator                 step_result.success = False
                                   all_succeeded = False
                                   BUT: current_data is STILL the analysis from step 2
                                   (the last successful step's output)

18    Orchestrator                 No more steps → exit loop
                                   WorkflowResult(
                                     success=False,  ← overall failed
                                     steps=[collect(✅), analyze(✅), write(❌)],
                                     final_output="## Highlights\n- Water streak 15d\n
                                                   ## Areas to Watch\n- Sleep declined...",
                                     total_tokens=1300,  ← only analysis tokens
                                     error="One or more steps failed",
                                   )

19    AI Service                   final_output is NOT empty — it's the analysis!
                                   Save to ai_insights anyway:
                                     (insight_type="weekly_report",
                                      content="## Highlights\n- Water streak 15d...")
                                   → User gets a structured analysis (not prose)
                                   → Less polished than a full report, but STILL USEFUL

WHAT THE USER SEES:
  Instead of: "# 📊 Hi Shreya! 🎉 Great week for water..."  (prose)
  They see:   "## Highlights\n- Water streak hit 15 days..."  (analysis)
  → Not as pretty, but all the insights are there.
  → Better than: "Report generation failed. Try again later." (nothing)
```

### Why Graceful Degradation Matters

```
STRATEGY A: Abort on first failure
  Step 1 ✅ → Step 2 ✅ → Step 3 ❌ → ERROR: "Report failed"
  User gets: NOTHING. Wasted ~1300 tokens on analysis for nothing.

STRATEGY B: Continue with partial output (our approach)
  Step 1 ✅ → Step 2 ✅ → Step 3 ❌ → Save analysis as report
  User gets: Structured analysis (highlights, concerns, recommendations)
  Value delivered: 80% of the full report's value
  Tokens wasted: 0 (the analysis IS useful)
```

---

<a name="triggers"></a>
## 5. How the Workflow Gets Triggered

### Trigger 1: Scheduled (Lambda — Sunday 10 PM UTC)

```
CloudWatch Event Rule (cron: 0 22 ? * SUN *)
  │
  ▼
Lambda: weekly_ai_report/handler.py
  │
  ├── For each user with weekly_report_enabled=True:
  │     │
  │     ├── Create WeeklyReportWorkflow(session, redis, user_id, user)
  │     ├── Create WorkflowOrchestrator(max_retries=2)
  │     ├── result = await orchestrator.run(workflow)
  │     │
  │     ├── Save result.final_output to ai_insights table
  │     └── Send notification email (if email_enabled)
  │
  └── Log: "weekly_reports_generated, users=50, success=48, failed=2"
```

### Trigger 2: On-Demand (API Endpoint)

```
POST /api/v1/ai/weekly-report
  Headers: Authorization: Bearer <token>
  │
  ▼
AI Router → AI Service → Same workflow pipeline
  │
  ▼
HTTP 200: {
  "report": "# 📊 Weekly Health Report...",
  "tokens_used": 4100,
  "duration_seconds": 8.8
}
```

The user clicks "Generate Report" in the frontend → same workflow runs for just that user.

---

<a name="costs"></a>
## 6. Token Cost Analysis

### Per Report

| Step | Tokens | Ollama | Groq | OpenAI GPT-4o |
|------|--------|--------|------|---------------|
| 1. Collect | 0 | $0 | $0 | $0 |
| 2. Analyze | ~1,300 | $0 | $0 | ~$0.01 |
| 3. Write | ~2,800 | $0 | $0 | ~$0.03 |
| **Total** | **~4,100** | **$0** | **$0** | **~$0.04** |

### Monthly (50 Users)

| Provider | Per Report | Weekly (50 users) | Monthly |
|----------|-----------|-------------------|---------|
| Ollama | $0 | $0 | **$0** |
| Groq | $0 | $0 | **$0** |
| OpenAI | $0.04 | $2.00 | **$8.00** |

At $8/month for 50 users with production-quality GPT-4o reports — very cost-effective.

### Retry Cost

Retries add 1 extra LLM call per failure. Typical retry rate: ~5%. For 50 weekly reports:
- 2-3 retries per week → ~$0.10 extra with OpenAI
- Negligible cost for significantly better reliability

---

<a name="summary"></a>
## 7. Workflow Module Summary

### What You Built (Parts 11–11b)

| Part | Files | What It Does |
|------|-------|-------------|
| **11** | — | Overview: agent vs workflow, 3 design decisions, 5 interview Q&A |
| **11a** | 5 files (full source) | base_workflow + orchestrator + 3 weekly report steps |
| **11b** | (this doc) | 3 execution flows, trigger mechanisms, cost analysis |

### By the Numbers

| Metric | Value |
|--------|-------|
| Python files | 6 (base, orchestrator, collector, analyzer, writer, __init__) |
| Workflow steps | 3 (collect → analyze → write) |
| LLM calls per report | 2 (analysis + writing) |
| Tokens per report | ~4,100 |
| Duration per report | ~8-15 seconds |
| Max retries per step | 2 |
| DB queries in step 1 | 5 (habits, logs, streaks, weekly, completion) |
| Temperature (analysis) | 0.4 (factual) |
| Temperature (writing) | 0.6 (creative) |
| Cost with Ollama/Groq | $0 |
| Cost with OpenAI (50 users/month) | ~$8 |

### AI Module Progress — Workflows Complete ✅

| Layer | Parts | Status |
|-------|-------|--------|
| LLM | 08a-08c | ✅ Strategy pattern, 3 providers, prompts, tokens |
| RAG | 09a-09c | ✅ Ingestion pipeline, pgvector search, retrieval |
| Agents | 10a-10d | ✅ 5 tools, memory, ReAct loop, flows |
| **Workflows** | **11-11b** | ✅ **Pipeline, orchestrator, weekly report, flows** |
| Service/Router | 12a-12d | Next |

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 11a: Workflow Pipeline](./phase4-part11a-ai-workflow-pipeline.md) |
| ➡️ Next | [Phase 4 Part 12: AI Service & Router Overview](./phase4-part12-ai-service-router-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Workflow Module — All Sub-Parts Complete ✅

| Sub-Part | Status | Document |
|----------|--------|----------|
| 11a | ✅ Done | Workflow Pipeline (5 files, full source code) |
| **11b** | ✅ **Done** | Workflow Connections & Flows |

---

**🎉 The Workflow layer is COMPLETE.**

*Three execution flows: happy path, retry path, degradation path. The weekly report generates in ~10 seconds with 2 LLM calls. At $0 with Ollama/Groq or $0.04 with OpenAI per report. Next: the AI service and router that ties all 39 AI files into 9 endpoints.*
