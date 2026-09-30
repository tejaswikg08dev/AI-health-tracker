# Mock LLM client — returns deterministic responses for testing

from typing import AsyncGenerator
from app.modules.ai.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse, ToolCall


class MockLLMClient(BaseLLMClient):
    """
    Fake LLM for testing — no API calls, deterministic responses.

    Usage in tests:
        mock_llm = MockLLMClient(response_text="Your sleep averaged 7 hours")
        agent = BaseAgent(llm=mock_llm, tools=[], system_prompt="...")
        result = await agent.run("How's my sleep?")
        assert "7 hours" in result
    """

    def __init__(
        self,
        response_text: str = "This is a mock AI response.",
        tool_calls: list[ToolCall] | None = None,
    ):
        self.response_text = response_text
        self.tool_calls = tool_calls or []
        self.call_count = 0
        self.last_messages: list[LLMMessage] = []

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_messages = messages

        # First call returns tool calls (if any), subsequent calls return text
        if self.tool_calls and self.call_count == 1:
            return LLMResponse(
                content="",
                tool_calls=self.tool_calls,
                input_tokens=100,
                output_tokens=50,
                model="mock-model",
            )

        return LLMResponse(
            content=self.response_text,
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            model="mock-model",
        )

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        for word in self.response_text.split():
            yield word + " "

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Return deterministic fake embeddings (768 dimensions)
        return [[float(i % 10) / 10 for i in range(768)] for _ in texts]
