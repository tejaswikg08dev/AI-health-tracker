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
