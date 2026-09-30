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
