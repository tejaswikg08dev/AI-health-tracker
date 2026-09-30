# ============================================================================
# Unit Tests — AI ReAct Agent
# ============================================================================
# Tests the agent loop with a mocked LLM — no real API calls.
# ============================================================================

import pytest
from app.modules.ai.agents.base_agent import BaseAgent
from app.modules.ai.agents.memory.short_term import ShortTermMemory
from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.ai.llm.base_client import LLMResponse, ToolCall
from tests.mocks.mock_llm_client import MockLLMClient


# ── Fake Tool for Testing ──
class FakeCalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Calculates a math expression"

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        }

    async def execute(self, **kwargs) -> str:
        return "Result: 42"


class TestBaseAgent:
    """Test the ReAct agent loop."""

    @pytest.mark.asyncio
    async def test_direct_response_no_tools(self):
        """Agent returns text response when no tool calls are made."""
        llm = MockLLMClient(response_text="Your sleep averaged 7 hours this week.")
        agent = BaseAgent(llm=llm, tools=[], system_prompt="You are a test agent.")

        result = await agent.run("How's my sleep?")

        assert "7 hours" in result
        assert llm.call_count == 1

    @pytest.mark.asyncio
    async def test_agent_calls_tool_then_responds(self):
        """Agent calls a tool, gets the result, then generates a final response."""
        # First call: LLM requests a tool call
        # Second call: LLM gives final answer using tool result
        tool_call = ToolCall(name="calculator", arguments={"expression": "6 * 7"})
        llm = MockLLMClient(
            response_text="The answer is 42, based on the calculation.",
            tool_calls=[tool_call],
        )
        tool = FakeCalculatorTool()
        agent = BaseAgent(llm=llm, tools=[tool], system_prompt="You are a test agent.")

        result = await agent.run("What is 6 times 7?")

        assert "42" in result
        assert llm.call_count == 2  # Tool call + final response

    @pytest.mark.asyncio
    async def test_agent_respects_max_iterations(self):
        """Agent stops after max_iterations even if LLM keeps requesting tools."""
        # LLM always requests tools — should hit the iteration limit
        tool_call = ToolCall(name="calculator", arguments={"expression": "1+1"})
        llm = MockLLMClient(response_text="Final answer.", tool_calls=[tool_call])
        # Override: make every call return tool_calls
        original_chat = llm.chat

        async def always_tool_call(*args, **kwargs):
            return LLMResponse(content="", tool_calls=[tool_call], input_tokens=10, output_tokens=10, model="mock")

        llm.chat = always_tool_call  # type: ignore

        tool = FakeCalculatorTool()
        agent = BaseAgent(llm=llm, tools=[tool], system_prompt="Test", max_iterations=3)

        # Should not hang — returns after max iterations
        result = await agent.run("Keep calculating forever")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_memory_stores_conversation(self):
        """Agent's memory stores user message and assistant response."""
        memory = ShortTermMemory(max_messages=20)
        llm = MockLLMClient(response_text="You're doing great!")
        agent = BaseAgent(llm=llm, tools=[], system_prompt="Test", memory=memory)

        await agent.run("How am I doing?")

        messages = memory.get_messages()
        assert len(messages) >= 2
        assert messages[0].role == "user"
        assert messages[0].content == "How am I doing?"
        assert messages[1].role == "assistant"
        assert "doing great" in messages[1].content

    @pytest.mark.asyncio
    async def test_unknown_tool_handled_gracefully(self):
        """Agent handles LLM requesting a tool that doesn't exist."""
        tool_call = ToolCall(name="nonexistent_tool", arguments={})
        llm = MockLLMClient(response_text="Sorry, I had trouble.", tool_calls=[tool_call])
        agent = BaseAgent(llm=llm, tools=[], system_prompt="Test")

        result = await agent.run("Do something")
        assert isinstance(result, str)  # Should not crash


class TestShortTermMemory:
    """Test the conversation buffer."""

    def test_add_and_retrieve(self):
        memory = ShortTermMemory(max_messages=10)
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi there!")

        messages = memory.get_messages()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_sliding_window(self):
        """Old messages are dropped when buffer is full."""
        memory = ShortTermMemory(max_messages=3)
        memory.add_user_message("msg1")
        memory.add_assistant_message("msg2")
        memory.add_user_message("msg3")
        memory.add_assistant_message("msg4")  # This should push msg1 out

        messages = memory.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "msg2"  # msg1 was dropped

    def test_clear(self):
        memory = ShortTermMemory()
        memory.add_user_message("Hello")
        memory.clear()
        assert memory.get_message_count() == 0
