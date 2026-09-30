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
