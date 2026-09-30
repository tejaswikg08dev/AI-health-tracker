# ============================================================================
# Agent — Base ReAct Agent
# ============================================================================
# WHAT THIS FILE DOES:
#   Implements the ReAct (Reason + Act) agent loop.
#   This is THE core AI agent pattern used by LangChain, CrewAI, AutoGen.
#   We build it FROM SCRATCH so you understand exactly how it works.
#
# THE REACT LOOP:
#   1. THINK  — LLM reasons about what to do next
#   2. ACT    — LLM calls a tool (query_logs, search_docs, etc.)
#   3. OBSERVE — Agent executes the tool and shows the result to the LLM
#   4. REPEAT — LLM thinks again: "Do I have enough info?" If not, goto 1.
#   5. ANSWER — LLM generates the final response using gathered data.
#
# EXAMPLE TRACE:
#   User: "Why am I tired this week?"
#
#   THINK 1: "I should check sleep data"
#   ACT 1:   tool_call: query_logs(habit_name="Sleep", days=7)
#   OBSERVE:  "Sleep data: Mon 5h, Tue 4.5h, Wed 6h..."
#
#   THINK 2: "Sleep is low. Let me check if exercise correlates"
#   ACT 2:   tool_call: correlate_habits(habit_a="Sleep", habit_b="Energy")
#   OBSERVE:  "Correlation: 0.78 (strong positive)"
#
#   THINK 3: "I have enough data to answer now"
#   ANSWER:   "Looking at your data, you averaged 5.2 hours of sleep this week..."
#
# MAX ITERATIONS:
#   We cap at 5 tool calls to prevent infinite loops.
#   If the agent can't figure it out in 5 steps, it gives its best answer.
#
# INTERVIEW GOLD:
#   "How do AI agents work?" → Explain this ReAct loop.
#   "How is an agent different from a chatbot?" → Chatbot = one LLM call.
#   Agent = multiple LLM calls with tool use between them.
# ============================================================================

from app.modules.ai.agents.memory.short_term import ShortTermMemory
from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.ai.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse
from app.shared.logging import get_logger

logger = get_logger(__name__)


class BaseAgent:
    """
    ReAct agent — Reason + Act loop with tool calling.

    The agent:
    1. Receives a user message
    2. Builds a prompt with: system instructions + tools + memory + user message
    3. Sends to LLM
    4. If LLM returns tool calls → executes tools → feeds results back → repeats
    5. If LLM returns text → that's the final answer

    Args:
        llm: The LLM client to use (Ollama, Groq, or OpenAI)
        tools: List of tools the agent can call
        system_prompt: Instructions that define the agent's behavior
        memory: Short-term conversation memory
        max_iterations: Maximum tool-calling rounds (prevents infinite loops)
    """

    def __init__(
        self,
        llm: BaseLLMClient,
        tools: list[BaseTool],
        system_prompt: str,
        memory: ShortTermMemory | None = None,
        max_iterations: int = 5,
    ):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.tool_schemas = [tool.to_openai_schema() for tool in tools]
        self.system_prompt = system_prompt
        self.memory = memory or ShortTermMemory()
        self.max_iterations = max_iterations
        self.total_tokens = 0

    async def run(self, user_message: str) -> str:
        """
        Run the agent on a user message.

        This is the main entry point. It:
        1. Adds the user message to memory
        2. Runs the ReAct loop (think → act → observe → repeat)
        3. Returns the final text response

        Returns:
            The agent's text response (may reference data from tools)
        """
        # Add user message to conversation memory
        self.memory.add_user_message(user_message)

        # Build the initial message list
        messages = self._build_messages()

        # ── ReAct Loop ──
        for iteration in range(self.max_iterations):
            logger.info(
                "agent_iteration",
                iteration=iteration + 1,
                max=self.max_iterations,
                message_count=len(messages),
            )

            # Ask the LLM: what should I do?
            response: LLMResponse = await self.llm.chat(
                messages=messages,
                tools=self.tool_schemas if self.tools else None,
                temperature=0.3,      # Lower temperature for more focused reasoning
                max_tokens=1024,
            )

            self.total_tokens += response.total_tokens

            # ── Case 1: LLM wants to call tools ──
            if response.has_tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.name
                    tool_args = tool_call.arguments

                    logger.info(
                        "agent_tool_call",
                        tool=tool_name,
                        args=str(tool_args)[:200],
                        iteration=iteration + 1,
                    )

                    # Execute the tool
                    if tool_name in self.tools:
                        try:
                            result = await self.tools[tool_name].execute(**tool_args)
                        except Exception as e:
                            result = f"Tool error: {str(e)}"
                            logger.error(
                                "agent_tool_error",
                                tool=tool_name,
                                error=str(e),
                            )
                    else:
                        result = f"Unknown tool: {tool_name}"
                        logger.warning("agent_unknown_tool", tool=tool_name)

                    # Add tool result to conversation
                    # The LLM needs to see what the tool returned
                    messages.append(LLMMessage(
                        role="assistant",
                        content=f"I'm checking your data using {tool_name}...",
                    ))
                    messages.append(LLMMessage(
                        role="tool",
                        content=f"[Tool: {tool_name}]\n{result}",
                    ))
                    self.memory.add_tool_result(tool_name, result)

                # Continue the loop — let the LLM decide what to do next
                continue

            # ── Case 2: LLM gives a text response (final answer) ──
            final_answer = response.content
            self.memory.add_assistant_message(final_answer)

            logger.info(
                "agent_completed",
                iterations=iteration + 1,
                total_tokens=self.total_tokens,
                answer_length=len(final_answer),
            )

            return final_answer

        # ── Max iterations reached ──
        # The agent couldn't figure it out in time.
        # Ask the LLM for its best answer with what it has.
        logger.warning("agent_max_iterations", max=self.max_iterations)

        messages.append(LLMMessage(
            role="user",
            content="Please provide your best answer with the information gathered so far.",
        ))

        response = await self.llm.chat(
            messages=messages,
            tools=None,          # No more tools — just answer
            temperature=0.5,
            max_tokens=1024,
        )

        self.total_tokens += response.total_tokens
        final_answer = response.content or "I wasn't able to fully answer your question. Could you try rephrasing it?"
        self.memory.add_assistant_message(final_answer)

        return final_answer

    def _build_messages(self) -> list[LLMMessage]:
        """
        Build the message list for the LLM.

        Structure:
        1. System prompt (defines agent behavior and available tools)
        2. Conversation history (from short-term memory)

        The system prompt is always first — it sets the context.
        The conversation history provides continuity across messages.
        """
        messages = [LLMMessage(role="system", content=self.system_prompt)]
        messages.extend(self.memory.get_messages())
        return messages
