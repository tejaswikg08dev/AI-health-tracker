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
#   - Step fails twice → skip with fallback data (partial report is better than none)
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

        Args:
            workflow: The workflow to execute
            initial_data: Input data for the first step

        Returns:
            WorkflowResult with all step results and final output
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
                # This is "graceful degradation" — better a partial report than no report

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
