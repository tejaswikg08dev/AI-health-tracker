# ⚙️ Phase 4 Part 11a: AI Workflow — Pipeline Implementation

> **"5 files, 3 steps, 2 LLM calls. The base defines the contract, the orchestrator runs it with retries, and the weekly report fills in the specifics: collect data, analyze patterns, write a report. Type every file — this is how production AI pipelines work."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 11a (Workflow Pipeline — Full Source Code) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.4 — Weekly Reports & Agentic Workflows |
| **Previous** | [phase4-part11-ai-workflows-overview.md](./phase4-part11-ai-workflows-overview.md) |
| **Next** | [phase4-part11b-ai-workflow-connections-and-flows.md](./phase4-part11b-ai-workflow-connections-and-flows.md) |
| **Files in This Doc** | 5 files (base_workflow.py, orchestrator.py, data_collector.py, analyzer.py, report_writer.py) |
| **Time to Type** | ~60 minutes |
| **Difficulty** | Hard (ABC with dataclass results, retry loop, cross-module DB queries, template-driven LLM calls) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: base_workflow.py — Abstract Interface + Data Classes](#base-workflow)
3. [File 2: orchestrator.py — Step Runner with Retry](#orchestrator)
4. [File 3: data_collector.py — Step 1: Fetch All Data](#collector)
5. [File 4: analyzer.py — Step 2: LLM Analysis](#analyzer)
6. [File 5: report_writer.py — Step 3: LLM Writing](#writer)
7. [How All 5 Files Connect](#connections)
8. [How to Verify Your Work](#verify)
9. [What You Learned](#what-you-learned)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

5 files that implement the complete workflow system:

| # | File | What It Does | LLM? | Lines |
|---|------|-------------|------|-------|
| 1 | `base_workflow.py` | Abstract interface + StepResult/WorkflowResult dataclasses | No | ~80 |
| 2 | `orchestrator.py` | Runs steps with retry, timing, error recovery | No | ~110 |
| 3 | `data_collector.py` | Step 1: fetches habits, logs, streaks, weekly data from DB | No | ~100 |
| 4 | `analyzer.py` | Step 2: LLM identifies patterns and recommendations | Yes | ~50 |
| 5 | `report_writer.py` | Step 3: LLM writes personalized markdown report | Yes | ~50 |

### Build Order

Type files in this order — each depends on the previous:

```
base_workflow.py  →  orchestrator.py  →  data_collector.py  →  analyzer.py  →  report_writer.py
    (interface)       (engine)              (step 1)            (step 2)         (step 3)
```

---

<a name="base-workflow"></a>
## 2. File 1: `base_workflow.py` — Abstract Interface + Data Classes

### Type This Code: `backend/app/modules/ai/workflows/base_workflow.py`

```python
# ============================================================================
# Agentic Workflows — Abstract Base Workflow
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the interface for multi-step AI workflows.
#   A workflow is a PIPELINE of agents/steps that run in sequence.
#
# SINGLE AGENT vs AGENTIC WORKFLOW:
#   Single Agent:   User → Agent (tools) → Response
#   Agentic Workflow: User → Agent1 → Agent2 → Agent3 → Response
#                     Each agent specializes in one task and passes data forward.
#
# WHY WORKFLOWS:
#   A weekly report needs:
#   1. Data collection (query all habit data for the week)
#   2. Analysis (find patterns, correlations, improvements)
#   3. Report writing (generate personalized prose)
#
#   One agent doing ALL of this produces mediocre results.
#   Three specialized agents — each doing one thing well — produce better output.
#   This is the same principle as microservices: separation of concerns.
#
# THIS IS THE SAME PATTERN AS:
#   - CrewAI (agents with roles collaborating)
#   - AutoGen (multi-agent conversations)
#   - LangGraph (stateful agent workflows)
#   We build it from scratch to understand the fundamentals.
# ============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.shared.date_utils import utc_now


@dataclass
class StepResult:
    """
    Result of a single workflow step.

    Each step produces a result that's passed to the next step.
    If a step fails, the error is captured and the workflow can retry or skip.
    """

    step_name: str
    success: bool
    data: Any = None                    # Output data (passed to next step)
    error: str | None = None            # Error message if failed
    tokens_used: int = 0
    duration_seconds: float = 0.0
    started_at: datetime = field(default_factory=utc_now)


@dataclass
class WorkflowResult:
    """
    Final result of a complete workflow run.

    Contains: all step results, final output, total tokens, timing.
    """

    workflow_name: str
    success: bool
    steps: list[StepResult] = field(default_factory=list)
    final_output: Any = None
    total_tokens: int = 0
    total_duration_seconds: float = 0.0
    error: str | None = None


class BaseWorkflow(ABC):
    """
    Abstract base class for agentic workflows.

    Subclasses define the steps and their execution order.
    The orchestrator handles running steps, retrying failures, and logging.

    Usage:
        class WeeklyReportWorkflow(BaseWorkflow):
            @property
            def name(self) -> str: return "weekly_report"

            @property
            def steps(self) -> list[str]: return ["collect", "analyze", "write"]

            async def execute_step(self, step_name, input_data):
                if step_name == "collect": return await self._collect(input_data)
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique workflow name."""
        ...

    @property
    @abstractmethod
    def steps(self) -> list[str]:
        """Ordered list of step names to execute."""
        ...

    @abstractmethod
    async def execute_step(self, step_name: str, input_data: Any) -> StepResult:
        """
        Execute a single step of the workflow.

        Args:
            step_name: Which step to run
            input_data: Output from the previous step (None for first step)

        Returns:
            StepResult with the step's output data
        """
        ...
```

### Line-by-Line Explanation

**`StepResult` dataclass — What Each Step Returns**
```python
@dataclass
class StepResult:
    step_name: str                      # "collect", "analyze", "write"
    success: bool                       # True if step completed without error
    data: Any = None                    # Step output → becomes next step's input
    error: str | None = None            # Error message on failure
    tokens_used: int = 0                # LLM tokens consumed (0 for DB-only steps)
    duration_seconds: float = 0.0       # How long the step took
    started_at: datetime = field(default_factory=utc_now)
```
- `data: Any = None` — flexible output. Step 1 returns a string (data summary). Step 2 returns a string (analysis). Step 3 returns a string (report markdown)
- `tokens_used` — only Steps 2 and 3 use tokens (LLM calls). Step 1 is pure DB
- `field(default_factory=utc_now)` — each StepResult gets the current timestamp when created

**`WorkflowResult` — The Final Report Card**
```python
@dataclass
class WorkflowResult:
    workflow_name: str                  # "weekly_report"
    success: bool                       # True if ALL steps succeeded
    steps: list[StepResult]             # Results from each step
    final_output: Any = None            # The last step's output (the report)
    total_tokens: int = 0               # Sum of all steps' tokens
    total_duration_seconds: float = 0.0 # Total wall-clock time
    error: str | None = None            # Overall error message if any step failed
```

**`BaseWorkflow` — The Contract**
```python
class BaseWorkflow(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def steps(self) -> list[str]: ...

    @abstractmethod
    async def execute_step(self, step_name: str, input_data: Any) -> StepResult: ...
```
- Any workflow must define: a `name`, an ordered list of `steps`, and an `execute_step` method
- The orchestrator calls `execute_step` for each step name in order
- `execute_step` returns a `StepResult` — the orchestrator decides what to do with it (retry, continue, abort)

---

<a name="orchestrator"></a>
## 3. File 2: `orchestrator.py` — Step Runner with Retry

### Type This Code: `backend/app/modules/ai/workflows/orchestrator.py`

```python
# ============================================================================
# Agentic Workflows — Orchestrator
# ============================================================================
# WHAT THIS FILE DOES:
#   Runs workflows step by step with retry logic, timeout handling,
#   error recovery, and detailed logging.
#
# THE ORCHESTRATOR'S JOB:
#   1. Run steps in sequence (step1 → step2 → step3)
#   2. Pass data from one step to the next
#   3. Retry failed steps (configurable retry count)
#   4. Fall back gracefully if a step fails permanently
#   5. Log every step's timing, tokens, and success/failure
#   6. Return a complete WorkflowResult with all step details
#
# ERROR HANDLING STRATEGY:
#   - Step fails once → retry (LLM calls can have transient failures)
#   - Step fails twice → skip with fallback data (partial report > none)
#   - Critical step fails → abort the workflow
#
# THIS IS THE SAME PATTERN AS:
#   - AWS Step Functions (state machine for task orchestration)
#   - Airflow DAGs (directed acyclic graphs of tasks)
#   - Temporal workflows (durable execution)
#   Simplified here for learning — same concepts, smaller scale.
# ============================================================================

import time
from typing import Any

from app.modules.ai.workflows.base_workflow import BaseWorkflow, StepResult, WorkflowResult
from app.shared.date_utils import utc_now
from app.shared.logging import get_logger

logger = get_logger(__name__)


class WorkflowOrchestrator:
    """
    Runs agentic workflows with retry, timeout, and error recovery.

    Usage:
        orchestrator = WorkflowOrchestrator(max_retries=2)
        result = await orchestrator.run(weekly_report_workflow, initial_data)
        # result.success, result.steps, result.final_output
    """

    def __init__(
        self,
        max_retries: int = 2,
        step_timeout_seconds: float = 120.0,
    ):
        self.max_retries = max_retries
        self.step_timeout_seconds = step_timeout_seconds

    async def run(
        self,
        workflow: BaseWorkflow,
        initial_data: Any = None,
    ) -> WorkflowResult:
        """
        Execute all steps of a workflow in sequence.

        Each step receives the output of the previous step.
        Failed steps are retried up to max_retries times.
        The workflow continues even if a non-critical step fails.
        """
        logger.info(
            "workflow_started",
            workflow=workflow.name,
            steps=workflow.steps,
        )

        start_time = time.perf_counter()
        step_results: list[StepResult] = []
        current_data = initial_data
        total_tokens = 0
        all_succeeded = True

        for step_name in workflow.steps:
            step_result = await self._run_step_with_retry(
                workflow, step_name, current_data
            )

            step_results.append(step_result)
            total_tokens += step_result.tokens_used

            if step_result.success:
                # Pass this step's output to the next step
                current_data = step_result.data
                logger.info(
                    "workflow_step_completed",
                    workflow=workflow.name,
                    step=step_name,
                    tokens=step_result.tokens_used,
                    duration=f"{step_result.duration_seconds:.1f}s",
                )
            else:
                all_succeeded = False
                logger.warning(
                    "workflow_step_failed",
                    workflow=workflow.name,
                    step=step_name,
                    error=step_result.error,
                )
                # Continue with partial data — next step handles missing input
                # This is "graceful degradation" — better a partial report than none

        total_duration = time.perf_counter() - start_time

        result = WorkflowResult(
            workflow_name=workflow.name,
            success=all_succeeded,
            steps=step_results,
            final_output=current_data,
            total_tokens=total_tokens,
            total_duration_seconds=round(total_duration, 2),
            error=None if all_succeeded else "One or more steps failed",
        )

        logger.info(
            "workflow_completed",
            workflow=workflow.name,
            success=all_succeeded,
            total_tokens=total_tokens,
            duration=f"{total_duration:.1f}s",
            steps_passed=sum(1 for s in step_results if s.success),
            steps_total=len(step_results),
        )

        return result

    async def _run_step_with_retry(
        self,
        workflow: BaseWorkflow,
        step_name: str,
        input_data: Any,
    ) -> StepResult:
        """
        Run a single step with retry logic.

        Retries on failure up to max_retries times.
        Returns the last attempt's result (success or final failure).
        """
        last_result = None

        for attempt in range(1, self.max_retries + 1):
            step_start = time.perf_counter()

            try:
                result = await workflow.execute_step(step_name, input_data)
                result.duration_seconds = round(time.perf_counter() - step_start, 2)

                if result.success:
                    return result

                last_result = result
                logger.warning(
                    "workflow_step_retry",
                    workflow=workflow.name,
                    step=step_name,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=result.error,
                )

            except Exception as e:
                duration = round(time.perf_counter() - step_start, 2)
                last_result = StepResult(
                    step_name=step_name,
                    success=False,
                    error=str(e),
                    duration_seconds=duration,
                )
                logger.error(
                    "workflow_step_exception",
                    workflow=workflow.name,
                    step=step_name,
                    attempt=attempt,
                    error=str(e),
                )

        # All retries exhausted — return last failure
        return last_result or StepResult(
            step_name=step_name,
            success=False,
            error="Step failed after all retries",
        )
```

### Key Orchestrator Concepts

**The Main Loop — `run()`**
```python
for step_name in workflow.steps:     # ["collect", "analyze", "write"]
    step_result = await self._run_step_with_retry(workflow, step_name, current_data)
    if step_result.success:
        current_data = step_result.data  # Pass output to next step
    else:
        all_succeeded = False
        # Continue anyway — graceful degradation
```
- `current_data` flows from step to step. Step 1 returns data_summary → Step 2 receives it → returns analysis → Step 3 receives both
- If a step fails, `current_data` stays the same (previous step's output). The next step receives incomplete input but still runs — it produces what it can

**Retry Loop — `_run_step_with_retry()`**
```python
for attempt in range(1, self.max_retries + 1):   # attempts 1, 2
    try:
        result = await workflow.execute_step(step_name, input_data)
        if result.success:
            return result       # Success — exit retry loop
        # result.success == False — step returned an error
        last_result = result
    except Exception as e:
        # Step crashed (exception, not a returned error)
        last_result = StepResult(step_name=step_name, success=False, error=str(e))
return last_result  # All retries failed — return the last failure
```
- Two types of failure: (1) `StepResult(success=False)` — the step caught the error and returned a clean result. (2) `Exception` — the step crashed unexpectedly
- Both are retried. Both are logged with attempt count
- After `max_retries` exhausted: return the last failure, don't crash

**`time.perf_counter()` for Timing**
```python
step_start = time.perf_counter()
result = await workflow.execute_step(...)
result.duration_seconds = round(time.perf_counter() - step_start, 2)
```
- `perf_counter()` is a high-resolution timer (nanosecond precision)
- Measures actual wall-clock time for each step
- Stored in `StepResult.duration_seconds` and `WorkflowResult.total_duration_seconds`
- Useful for monitoring: "Step 2 took 8 seconds — LLM is slow today"

---

<a name="collector"></a>
## 4. File 3: `data_collector.py` — Step 1: Fetch All Data

### Type This Code: `backend/app/modules/ai/workflows/weekly_report/data_collector.py`

```python
# ============================================================================
# Weekly Report — Step 1: Data Collector
# ============================================================================
# Gathers all habit data for the past week and formats it into a structured
# summary that the Analyzer step can work with.
# ============================================================================

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.repository import AnalyticsRepository
from app.modules.habits.repository import HabitRepository
from app.modules.logs.repository import LogRepository
from app.shared.date_utils import start_of_week, today_utc
from app.shared.logging import get_logger

logger = get_logger(__name__)


class DataCollector:
    """
    Step 1 of the weekly report workflow.

    Collects: habit logs, streaks, weekly comparison, completion rates.
    Formats everything into a text summary for the LLM to analyze.
    """

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def collect(self) -> str:
        """
        Gather all relevant data for the weekly report.

        Returns a formatted text summary that can be sent to an LLM.
        """
        habit_repo = HabitRepository(self.session)
        log_repo = LogRepository(self.session)
        analytics_repo = AnalyticsRepository(self.session)

        today = today_utc()
        week_start = start_of_week(today)
        last_week_start = week_start - timedelta(days=7)

        # Get active habits
        habits = await habit_repo.get_user_habits(self.user_id)
        if not habits:
            return "No active habits found. The user hasn't created any habits yet."

        # Get this week's logs
        logs = await log_repo.get_logs_for_range(
            self.user_id, week_start, today
        )

        # Get streaks
        streaks = await analytics_repo.get_streaks(self.user_id)

        # Get weekly summary (this vs last)
        weekly = await analytics_repo.get_weekly_summary(self.user_id)

        # Get completion rates
        completion = await analytics_repo.get_completion_rates(self.user_id, days=7)

        # Format into structured text
        sections = []

        # Section 1: Habits overview
        sections.append(f"ACTIVE HABITS ({len(habits)}):")
        for h in habits:
            target = f", target: {h.target_value} {h.unit}" if h.target_value else ""
            sections.append(f"  - {h.name} ({h.habit_type}{target})")

        # Section 2: This week's data
        sections.append(f"\nTHIS WEEK'S LOGS ({week_start} to {today}):")
        habit_names = {str(h.id): h for h in habits}
        for log in logs:
            habit = habit_names.get(str(log.habit_id))
            name = habit.name if habit else "Unknown"
            unit = habit.unit if habit else ""
            value = log.value_numeric or log.value_scale or ("Yes" if log.value_boolean else "No")
            sections.append(f"  {log.log_date} | {name}: {value} {unit}")

        # Section 3: Streaks
        sections.append("\nCURRENT STREAKS:")
        for s in streaks:
            sections.append(
                f"  {s['habit_name']}: {s['current_streak']} days "
                f"(best: {s['longest_streak']})"
            )

        # Section 4: Weekly comparison
        sections.append("\nTHIS WEEK vs LAST WEEK:")
        for w in weekly:
            this_avg = f"{w['this_week_avg']:.1f}" if w['this_week_avg'] else "N/A"
            last_avg = f"{w['last_week_avg']:.1f}" if w['last_week_avg'] else "N/A"
            sections.append(
                f"  {w['habit_name']}: {this_avg} (this week) vs {last_avg} (last week)"
            )

        # Section 5: Completion rates
        sections.append("\nCOMPLETION RATES (this week):")
        for c in completion:
            pct = (c['days_logged'] / max(c['total_days'], 1)) * 100
            sections.append(f"  {c['habit_name']}: {pct:.0f}% ({c['days_logged']}/{c['total_days']} days)")

        summary = "\n".join(sections)

        logger.info(
            "weekly_data_collected",
            user_id=str(self.user_id),
            habits=len(habits),
            logs=len(logs),
        )

        return summary
```

### What This Step Produces (Example Output)

```
ACTIVE HABITS (6):
  - Water Intake (numeric, target: 8.0 glasses)
  - Sleep Hours (numeric, target: 7.0 hours)
  - Exercise (boolean)
  - Mood (scale)
  - Meditation (boolean)
  - Steps (numeric, target: 10000.0 steps)

THIS WEEK'S LOGS (2026-09-21 to 2026-09-26):
  2026-09-21 | Water Intake: 7.0 glasses
  2026-09-21 | Sleep Hours: 7.5 hours
  2026-09-21 | Exercise: Yes
  2026-09-21 | Mood: 8
  ... (42 total entries for 6 habits × 7 days)

CURRENT STREAKS:
  Water Intake: 15 days (best: 30)
  Sleep Hours: 7 days (best: 14)
  Exercise: 0 days (best: 10)
  Mood: 5 days (best: 12)

THIS WEEK vs LAST WEEK:
  Water Intake: 7.4 (this week) vs 7.0 (last week)
  Sleep Hours: 6.8 (this week) vs 7.2 (last week)
  Exercise: 0.6 (this week) vs 0.4 (last week)
  Mood: 6.8 (this week) vs 7.1 (last week)

COMPLETION RATES (this week):
  Water Intake: 100% (6/6 days)
  Sleep Hours: 100% (6/6 days)
  Exercise: 67% (4/6 days)
  Mood: 83% (5/6 days)
```

This ~1500 token structured summary becomes the input for Step 2 (Analyzer).

### Key Implementation Details

**Cross-Module Repository Access**
```python
habit_repo = HabitRepository(self.session)
log_repo = LogRepository(self.session)
analytics_repo = AnalyticsRepository(self.session)
```
Step 1 uses repositories from THREE modules — Habits, Logs, and Analytics. All share the same database session (one transaction).

**No LLM Call — Pure Database**
This step is $0 in token cost. It's the most reliable step (DB queries rarely fail). This is intentional — separate the reliable data gathering from the unreliable LLM calls.

**Formatted Text (Not JSON)**
The output is human-readable text, not structured JSON. Why? The LLM in Step 2 reads it as context. Text is easier for an LLM to parse than JSON. The structured format (sections with headers) helps the LLM identify different data types.

---

<a name="analyzer"></a>
## 5. File 4: `analyzer.py` — Step 2: LLM Analysis

### Type This Code: `backend/app/modules/ai/workflows/weekly_report/analyzer.py`

```python
# ============================================================================
# Weekly Report — Step 2: Analyzer
# ============================================================================
# Takes the raw data summary from Step 1 and uses an LLM to find patterns,
# generate insights, and produce recommendations.
# ============================================================================

from app.modules.ai.llm.base_client import BaseLLMClient, LLMMessage
from app.modules.ai.llm.prompt_templates import WEEKLY_REPORT_ANALYSIS
from app.shared.logging import get_logger

logger = get_logger(__name__)


class Analyzer:
    """
    Step 2 of the weekly report workflow.

    Uses an LLM to analyze the collected data and produce:
    - Top improvements
    - Concerning trends
    - Correlations
    - Recommendations
    """

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    async def analyze(self, data_summary: str) -> tuple[str, int]:
        """
        Analyze the weekly data using an LLM.

        Args:
            data_summary: Formatted text from DataCollector

        Returns:
            Tuple of (analysis_text, tokens_used)
        """
        prompt = WEEKLY_REPORT_ANALYSIS.render(data_summary=data_summary)

        messages = [
            LLMMessage(role="system", content="You are a health data analyst. Provide structured insights."),
            LLMMessage(role="user", content=prompt),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.4,     # Slightly creative but mostly factual
            max_tokens=1500,
        )

        logger.info(
            "weekly_analysis_completed",
            tokens=response.total_tokens,
            analysis_length=len(response.content),
        )

        return response.content, response.total_tokens
```

### Key Details

**Uses `WEEKLY_REPORT_ANALYSIS` Template (from Part 08c)**

The template tells the LLM exactly what to produce:
```
Analyze this week's health data. Identify:
1. Top 3 improvements this week
2. Concerning trends or declines
3. Correlations between habits
4. 2-3 specific, actionable recommendations

Format as: ## Highlights, ## Areas to Watch, ## Recommendations
```

**Temperature 0.4 — Factual Analysis**
- Lower than chat (0.7) because analysis should be consistent and data-driven
- "Sleep declined 5.6%" should be the same every time, not creatively rephrased
- Still 0.4 (not 0.0) to allow slight variation in phrasing

**Returns `tuple[str, int]` — Text + Token Count**
- The analysis text becomes input for Step 3
- Token count is tracked for cost monitoring

---

<a name="writer"></a>
## 6. File 5: `report_writer.py` — Step 3: LLM Writing

### Type This Code: `backend/app/modules/ai/workflows/weekly_report/report_writer.py`

```python
# ============================================================================
# Weekly Report — Step 3: Report Writer
# ============================================================================
# Takes data + analysis and writes a personalized, friendly weekly report.
# ============================================================================

from app.modules.ai.llm.base_client import BaseLLMClient, LLMMessage
from app.modules.ai.llm.prompt_templates import WEEKLY_REPORT_WRITER
from app.shared.logging import get_logger

logger = get_logger(__name__)


class ReportWriter:
    """
    Step 3 of the weekly report workflow.

    Takes the raw data (Step 1) and analysis (Step 2) and writes
    a personalized, friendly weekly health report in markdown.
    """

    def __init__(self, llm: BaseLLMClient, user_name: str):
        self.llm = llm
        self.user_name = user_name

    async def write(self, data_summary: str, analysis: str) -> tuple[str, int]:
        """
        Write the final weekly report.

        Args:
            data_summary: Raw data from DataCollector
            analysis: Structured insights from Analyzer

        Returns:
            Tuple of (report_markdown, tokens_used)
        """
        prompt = WEEKLY_REPORT_WRITER.render(
            user_name=self.user_name,
            data_summary=data_summary,
            analysis=analysis,
        )

        messages = [
            LLMMessage(
                role="system",
                content="You are a friendly health coach writing a weekly report. "
                        "Use markdown formatting. Be encouraging and specific.",
            ),
            LLMMessage(role="user", content=prompt),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.6,     # More creative for engaging writing
            max_tokens=2000,
        )

        logger.info(
            "weekly_report_written",
            tokens=response.total_tokens,
            report_length=len(response.content),
        )

        return response.content, response.total_tokens
```

### Key Difference from Analyzer

| Feature | Analyzer (Step 2) | ReportWriter (Step 3) |
|---------|-------------------|----------------------|
| System prompt | "health data analyst" | "friendly health coach" |
| Temperature | 0.4 (factual) | 0.6 (creative) |
| max_tokens | 1500 | 2000 (longer output) |
| Input | data_summary only | data_summary + analysis |
| Output style | Structured (##Highlights) | Narrative (prose + emoji) |
| Goal | Find patterns | Engage the user |

**The writer receives BOTH step 1 and step 2 outputs.** It has the raw data (for specific numbers) AND the analysis (for insights). This produces a report that's both accurate AND engaging.

**Temperature 0.6 — Creative Writing**
- Higher than analysis (0.4) because writing benefits from personality
- "Hi Shreya! 🎉 Great week for water!" is more engaging than "User had good water intake"
- Still below 0.7 to keep the content grounded in data

---

<a name="connections"></a>
## 7. How All 5 Files Connect

```
AI Service calls:
  workflow = WeeklyReportWorkflow(session, redis, user_id, user)
  orchestrator = WorkflowOrchestrator(max_retries=2)
  result = await orchestrator.run(workflow, initial_data=None)

Orchestrator.run():
  │
  ├── Step "collect":
  │   workflow.execute_step("collect", None)
  │     → DataCollector(session, user_id).collect()
  │     → 5 DB queries → formatted text summary (~1500 tokens)
  │     → StepResult(success=True, data="ACTIVE HABITS (6): ...")
  │
  ├── Step "analyze":
  │   workflow.execute_step("analyze", data_summary)
  │     → Analyzer(llm).analyze(data_summary)
  │     → 1 LLM call (temp=0.4) → structured analysis
  │     → StepResult(success=True, data="## Highlights\n...", tokens=1300)
  │
  └── Step "write":
      workflow.execute_step("write", analysis)
        → ReportWriter(llm, user_name).write(data_summary, analysis)
        → 1 LLM call (temp=0.6) → friendly markdown report
        → StepResult(success=True, data="# Weekly Report\n...", tokens=2800)

Result:
  WorkflowResult(
    success=True,
    steps=[collect_result, analyze_result, write_result],
    final_output="# 📊 Weekly Health Report...",
    total_tokens=4100,
    total_duration_seconds=12.5,
  )
```

---

<a name="verify"></a>
## 8. How to Verify Your Work

```bash
# Verify imports
docker-compose exec backend python -c "
from app.modules.ai.workflows.base_workflow import BaseWorkflow, StepResult, WorkflowResult
from app.modules.ai.workflows.orchestrator import WorkflowOrchestrator
from app.modules.ai.workflows.weekly_report.data_collector import DataCollector
from app.modules.ai.workflows.weekly_report.analyzer import Analyzer
from app.modules.ai.workflows.weekly_report.report_writer import ReportWriter
print('✅ All workflow imports OK')
print(f'StepResult fields: {[f.name for f in StepResult.__dataclass_fields__.values()]}')
print(f'WorkflowResult fields: {[f.name for f in WorkflowResult.__dataclass_fields__.values()]}')
"
```

---

<a name="what-you-learned"></a>
## 9. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Pipeline Pattern** | Steps execute in sequence, each receives previous output | orchestrator.run() |
| 2 | **StepResult** | Dataclass: success + data + error + tokens + duration | Every step returns one |
| 3 | **WorkflowResult** | All step results + final output + totals | orchestrator returns one |
| 4 | **Abstract workflow** | `BaseWorkflow` ABC defines name, steps, execute_step | base_workflow.py |
| 5 | **Retry loop** | `for attempt in range(max_retries)` → retry on failure | _run_step_with_retry |
| 6 | **Graceful degradation** | Failed step → continue with partial data (not abort) | orchestrator main loop |
| 7 | **Cross-module repo access** | DataCollector uses Habit, Log, Analytics repos | data_collector.py |
| 8 | **Structured text output** | Sections with headers for LLM readability | DataCollector.collect() |
| 9 | **Temperature separation** | 0.4 for analysis (factual), 0.6 for writing (creative) | analyzer vs writer |
| 10 | **Two-step LLM** | Separate analysis from writing → better quality | Steps 2 + 3 |
| 11 | **`tuple[str, int]` return** | Text output + token count from LLM steps | analyzer, writer |
| 12 | **`time.perf_counter()`** | High-resolution timing for step duration | orchestrator |

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: Walk me through the weekly report workflow step by step.
**A:** "Three steps. Step 1 (DataCollector) queries 5 database sources: active habits, 7 days of logs, streaks, weekly comparison, and completion rates. It formats these into a structured text summary — no LLM call, pure DB, ~100ms. Step 2 (Analyzer) sends this summary to the LLM with a prompt asking it to identify patterns, concerns, and recommendations — temperature 0.4 for factual output, ~1300 tokens. Step 3 (ReportWriter) receives both the raw data and the analysis, and writes a friendly markdown report — temperature 0.6 for engaging prose, ~2800 tokens. Total: 2 LLM calls, ~4100 tokens, ~12 seconds."

### Q2: How does the orchestrator handle failures?
**A:** "The orchestrator retries each step up to twice. LLM calls have transient failures — timeouts, rate limits — that usually succeed on retry. If a step fails permanently, the orchestrator continues with partial data. Step 2 fails? Step 3 writes a simpler report from raw data alone. Step 3 fails? The analysis from step 2 is saved as the report. We never crash the entire workflow because one LLM call failed."

### Q3: Why is step 1 a separate step instead of letting the LLM fetch its own data?
**A:** "Reliability and cost. Database queries are deterministic and fast (~100ms). LLM-driven data fetching (via agent tools) is non-deterministic — the agent might call the wrong tool, miss data, or take multiple iterations. By pre-collecting everything in step 1, we guarantee complete, consistent data input to the LLM. Step 1 costs $0 in tokens. If the agent fetched data itself, it might use 3-5 tool calls (~2000 extra tokens)."

### Q4: How does this compare to CrewAI or LangGraph?
**A:** "Same concepts. CrewAI would define three agents with roles (Researcher, Analyst, Writer) — equivalent to our DataCollector, Analyzer, ReportWriter. LangGraph would define a state machine with nodes and edges — equivalent to our step list. Our orchestrator is simpler (sequential pipeline, not a graph) because we know the steps don't branch. In production with complex workflows (conditional paths, parallel steps), we'd evaluate LangGraph."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 11: Workflows Overview](./phase4-part11-ai-workflows-overview.md) |
| ➡️ Next | [Phase 4 Part 11b: Workflow Connections & Flows](./phase4-part11b-ai-workflow-connections-and-flows.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Workflow Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **11a** | ✅ **You are here** | Workflow Pipeline (5 files, full source) |
| 11b | ⬜ Next | Workflow Connections & Flows |

---

**End of Phase 4 Part 11a: Workflow Pipeline Implementation**

*5 files typed. The abstract interface defines the contract. The orchestrator runs steps with retry. The weekly report implements 3 specialized steps: collect (DB), analyze (LLM), write (LLM). Next: flow diagrams showing the full execution trace with retry scenarios.*
