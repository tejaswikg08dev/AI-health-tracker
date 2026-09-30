# 🧠 Phase 4 Part 10c: AI Agent — ReAct Loop ★★★

> **"This is THE file. 100 lines of Python that implement the core reasoning loop used by every major AI agent framework — LangChain, CrewAI, AutoGen. The LLM thinks, calls a tool, observes the result, thinks again, and eventually answers. Understanding this loop means understanding how modern AI agents work."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 10c (★★★ ReAct Agent Loop — HARDEST AI DOC) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.3 — AI Agent + Tools |
| **Previous** | [phase4-part10b-ai-agent-memory.md](./phase4-part10b-ai-agent-memory.md) |
| **Next** | [phase4-part10d-ai-agent-connections-and-flows.md](./phase4-part10d-ai-agent-connections-and-flows.md) |
| **Files in This Doc** | 1 file (base_agent.py) — THE core agent implementation |
| **Time to Type** | ~45 minutes |
| **Difficulty** | ★★★ HARD (async loop, LLM orchestration, tool dispatch, error recovery) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [The ReAct Loop — Visual](#react-visual)
3. [File: base_agent.py — Full Source Code](#source)
4. [The Loop Line-by-Line](#line-by-line)
5. [Execution Trace — Real Example](#trace)
6. [Design Decisions](#design-decisions)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

One file — `base_agent.py` — that implements the ReAct (Reason + Act) loop. This is the same pattern behind:
- **LangChain** AgentExecutor
- **CrewAI** Agent
- **AutoGen** AssistantAgent
- **OpenAI** Assistants API

We build it from scratch in ~100 lines so you understand exactly how it works.

### What the Agent Does (vs a Chatbot)

```
CHATBOT (1 LLM call):
  Input: messages → LLM → Output: text response

AGENT (N LLM calls with tools):
  Input: messages
    → LLM call 1: "I need sleep data" → tool_call: query_logs
    → Tool executes → result fed back
    → LLM call 2: "Let me check correlations" → tool_call: correlate
    → Tool executes → result fed back
    → LLM call 3: "I have enough info" → text response
  Output: data-driven answer
```

---

<a name="react-visual"></a>
## 2. The ReAct Loop — Visual

```
              ┌─────────────────────────────────────────────────┐
              │              BASE AGENT                          │
              │                                                  │
  User msg ──>│  _build_messages()                               │
              │  [system_prompt] + [conversation_history]        │
              │          │                                       │
              │          ▼                                       │
              │  ┌─── FOR iteration IN range(max_iterations) ──┐│
              │  │                                              ││
              │  │  llm.chat(messages, tools=tool_schemas)      ││
              │  │          │                                    ││
              │  │          ▼                                    ││
              │  │  ┌─── response.has_tool_calls? ────┐        ││
              │  │  │                                  │        ││
              │  │  │ YES                           NO │        ││
              │  │  │                                  │        ││
              │  │  ▼                                  ▼        ││
              │  │  Execute each tool          Return content   ││
              │  │  Add results to messages    (final answer)   ││
              │  │  CONTINUE loop                 EXIT ──────>  ││
              │  │  │                                           ││
              │  │  └───────────────────────────────────────────┘│
              │  │                                              ││
              │  └─── END FOR (max iterations reached) ────────┘│
              │          │                                       │
              │          ▼                                       │
              │  Force answer: "Please give your best answer"    │
              │  llm.chat(messages, tools=None)                  │
              │          │                                       │
              └──────────┼───────────────────────────────────────┘
                         ▼
                  Return final answer
```

---

<a name="source"></a>
## 3. File: `base_agent.py` — Full Source Code

### Type This Code: `backend/app/modules/ai/agents/base_agent.py`

```python
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
                temperature=0.3,      # Lower temperature for focused reasoning
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
        """
        messages = [LLMMessage(role="system", content=self.system_prompt)]
        messages.extend(self.memory.get_messages())
        return messages
```

---

<a name="line-by-line"></a>
## 4. The Loop Line-by-Line

### Constructor — Wire Everything Together

```python
def __init__(self, llm, tools, system_prompt, memory=None, max_iterations=5):
    self.llm = llm                                          # LLM client (Strategy pattern)
    self.tools = {tool.name: tool for tool in tools}        # name → tool dict (for dispatch)
    self.tool_schemas = [tool.to_openai_schema() for tool in tools]  # For LLM prompt
    self.system_prompt = system_prompt                      # Agent persona + rules
    self.memory = memory or ShortTermMemory()               # Conversation buffer
    self.max_iterations = max_iterations                    # Safety cap: 5 tool rounds
    self.total_tokens = 0                                   # Cost tracking
```

**`self.tools = {tool.name: tool for tool in tools}`** — Dict comprehension. Creates a lookup table:
```python
{"query_logs": QueryLogsTool(...), "correlate": CorrelateTool(...), ...}
```
When the LLM says `tool_call.name = "query_logs"`, we look it up: `self.tools["query_logs"]`.

**`self.tool_schemas = [tool.to_openai_schema() for tool in tools]`** — List of tool definitions sent to the LLM. The LLM sees THESE to decide which tools to call.

### The Main Loop — `run()`

**Step 1: Add message + build context**
```python
self.memory.add_user_message(user_message)
messages = self._build_messages()
# messages = [system_prompt, ...conversation_history..., user_message]
```

**Step 2: The for loop**
```python
for iteration in range(self.max_iterations):  # max 5 rounds
```
Each iteration is ONE LLM call. The LLM either returns tool calls (continue looping) or text (exit loop).

**Step 3: Call the LLM**
```python
response = await self.llm.chat(
    messages=messages,
    tools=self.tool_schemas if self.tools else None,
    temperature=0.3,      # Low creativity — we want focused reasoning
    max_tokens=1024,
)
```
- `tools=self.tool_schemas` — the LLM sees all 5 tool definitions
- `temperature=0.3` — low randomness for consistent tool selection
- Returns `LLMResponse` with either `content` (text) or `tool_calls` (actions)

**Step 4a: Tool calls (continue loop)**
```python
if response.has_tool_calls:
    for tool_call in response.tool_calls:
        tool_name = tool_call.name        # e.g., "query_logs"
        tool_args = tool_call.arguments   # e.g., {"habit_name": "Sleep", "days": 7}

        # Execute the tool
        if tool_name in self.tools:
            result = await self.tools[tool_name].execute(**tool_args)
        else:
            result = f"Unknown tool: {tool_name}"

        # Feed result back to LLM
        messages.append(LLMMessage(role="assistant", content=f"Checking {tool_name}..."))
        messages.append(LLMMessage(role="tool", content=f"[Tool: {tool_name}]\n{result}"))

    continue  # Back to top of loop — LLM sees tool results and decides next step
```

This is the CORE of the agent. The LLM decides, the agent executes, the result goes back. Repeat.

**Step 4b: Text response (exit loop)**
```python
final_answer = response.content
self.memory.add_assistant_message(final_answer)
return final_answer
```

If the LLM returns text (no tool calls), it's the final answer. Save to memory and return.

**Step 5: Max iterations safety**
```python
# After 5 rounds with no answer:
messages.append(LLMMessage(
    role="user",
    content="Please provide your best answer with the information gathered so far.",
))
response = await self.llm.chat(messages=messages, tools=None)  # Force text answer
```

If the agent calls tools 5 times without answering, we force a final response by:
1. Adding an explicit "give your best answer" instruction
2. Calling LLM with `tools=None` — it CAN'T call more tools, MUST give text

---

<a name="trace"></a>
## 5. Execution Trace — Real Example

```
User: "Why is my mood low this week?"

══ ITERATION 1 ══════════════════════════════════════════════════
  messages = [system_prompt, user: "Why is my mood low this week?"]
  llm.chat(messages, tools=[5 tool schemas])

  LLM thinks: "I need mood data for this week"
  LLM returns: tool_calls=[ToolCall(name="query_logs", args={"habit_name":"Mood","days":7})]

  Agent: self.tools["query_logs"].execute(habit_name="Mood", days=7)
  Tool returns: "Mood data:\n  Sep 20: 8\n  Sep 21: 7\n  Sep 22: 5\n  Sep 23: 4\n  Sep 24: 5\n  Sep 25: 6\n  Sep 26: 5"

  messages += [assistant: "Checking query_logs...", tool: "[Tool: query_logs]\nMood data: ..."]

══ ITERATION 2 ══════════════════════════════════════════════════
  messages = [system, user, assistant, tool_result, ...]
  llm.chat(messages, tools=[5 tool schemas])

  LLM thinks: "Mood dropped mid-week. Let me check what correlates with mood."
  LLM returns: tool_calls=[ToolCall(name="correlate", args={"days":30})]

  Agent: self.tools["correlate"].execute(days=30)
  Tool returns: "Correlations:\n  Sleep ↔ Mood: r=0.72 (strong positive)\n  Exercise ↔ Mood: r=0.45 (moderate)"

  messages += [assistant: "Checking correlate...", tool: "[Tool: correlate]\nCorrelations: ..."]

══ ITERATION 3 ══════════════════════════════════════════════════
  messages = [system, user, assistant, tool1_result, assistant, tool2_result, ...]
  llm.chat(messages, tools=[5 tool schemas])

  LLM thinks: "Sleep correlates strongly with mood. Let me check sleep data."
  LLM returns: tool_calls=[ToolCall(name="query_logs", args={"habit_name":"Sleep","days":7})]

  Agent: self.tools["query_logs"].execute(habit_name="Sleep", days=7)
  Tool returns: "Sleep data:\n  Sep 20: 7.5h\n  Sep 21: 7.0h\n  Sep 22: 5.0h\n  Sep 23: 4.5h\n  Sep 24: 5.5h\n  Sep 25: 6.0h\n  Sep 26: 5.0h"

══ ITERATION 4 ══════════════════════════════════════════════════
  LLM thinks: "I have mood data, correlations, and sleep data. I can answer now."
  LLM returns: content="Your mood dropped this week (avg 5.7, down from 7.2)..."

  → NO tool calls → this is the FINAL ANSWER
  → Return to user

FINAL ANSWER:
  "Your mood has been lower this week — averaging 5.7 out of 10, down from
   last week's 7.2. Looking at the data, this strongly correlates with your
   sleep decline. Your sleep dropped from 7.5 hours early in the week to
   4.5-5.5 hours from Wednesday onward.

   The correlation between your sleep and mood is 0.72 (strong positive),
   meaning better sleep consistently corresponds to better mood for you.

   Suggestion: Try getting back to 7+ hours tonight. Your data shows
   that on days you sleep more than 7 hours, your mood averages 7.5."

STATS: 4 iterations, 3 tool calls, ~3500 total tokens
```

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision: Temperature 0.3 for Agent Reasoning

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Agent Temperature                                 │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: temperature=0.3 for agent reasoning (lower than chat 0.7)  │
│                                                                     │
│  WHY:                                                               │
│  • Tool selection must be deterministic — "query_logs" not random   │
│  • Argument generation must be precise — {"days": 7} not {"days": π}│
│  • Lower temperature = more focused, reliable tool usage            │
│  • Higher temperature = creative but sometimes hallucinates tools   │
│                                                                     │
│  WHY NOT 0.0:                                                       │
│  • 0.0 is completely deterministic — can get stuck in loops          │
│  • 0.3 allows slight variation in phrasing while staying focused    │
│                                                                     │
│  COMPARISON:                                                        │
│  • Agent reasoning: 0.3 (precise tool usage)                        │
│  • Chat responses: 0.7 (natural conversation)                       │
│  • Creative writing: 0.9+ (brainstorming, variety)                  │
│                                                                     │
│  INTERVIEW TIP: "We use temperature 0.3 for agent reasoning —      │
│  lower than the default 0.7 — because tool selection and argument  │
│  generation need to be precise, not creative. Higher temperatures   │
│  cause the LLM to sometimes hallucinate tool names or generate     │
│  invalid arguments."                                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision: Max 5 Iterations

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Iteration Limit                                   │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: max_iterations=5 (5 tool-calling rounds)                   │
│                                                                     │
│  WHY 5:                                                             │
│  • Most questions need 1-3 tool calls (data + context + maybe docs) │
│  • 5 gives headroom for complex multi-step reasoning                │
│  • Each iteration = 1 LLM call ($0.01-0.05 with GPT-4)             │
│  • 5 iterations = $0.05-0.25 max cost per question                  │
│                                                                     │
│  WHY NOT 10+:                                                       │
│  • Diminishing returns — if 5 tools didn't help, 10 won't either   │
│  • Cost: 10 iterations = $0.10-0.50 per question (expensive)        │
│  • Risk of infinite loops (LLM keeps calling the same tool)         │
│                                                                     │
│  SAFETY NET: After 5 iterations, we force an answer by calling      │
│  the LLM with tools=None and a "give your best answer" instruction. │
│  The agent always responds — never hangs.                           │
│                                                                     │
│  INTERVIEW TIP: "We cap at 5 iterations to prevent infinite loops   │
│  and control costs. If the agent needs more than 5 tool calls, the  │
│  question is likely too complex for a single interaction. After 5,  │
│  we force a best-effort answer."                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **ReAct Loop** | Think → Act → Observe → Repeat → Answer | `run()` for-loop |
| 2 | **Tool dispatch** | `self.tools[name].execute(**args)` — name-based lookup | Tool call handling |
| 3 | **Dict comprehension** | `{tool.name: tool for tool in tools}` — name→tool map | Constructor |
| 4 | **`response.has_tool_calls`** | LLMResponse property: True if tools requested | Loop branching |
| 5 | **`continue`** | Skip to next loop iteration (after processing tools) | After tool execution |
| 6 | **`return`** inside loop | Exit the loop AND the function (final answer) | Case 2: text response |
| 7 | **Max iteration safety** | Force answer after 5 rounds with `tools=None` | End of for-loop |
| 8 | **`temperature=0.3`** | Low randomness for precise tool selection | `llm.chat()` call |
| 9 | **Message accumulation** | Each tool result is appended to `messages` | Growing context |
| 10 | **Token tracking** | `self.total_tokens += response.total_tokens` | Cost monitoring |
| 11 | **Error recovery** | `try/except` around tool execution — errors don't crash agent | Tool call handling |
| 12 | **Unknown tool handling** | `if tool_name in self.tools` — graceful fallback | Tool dispatch |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: Walk me through how the ReAct agent processes a question.
**A:** "The user sends a message. The agent builds a prompt: system instructions, conversation history, and the user's question. It calls the LLM with tool schemas. The LLM either returns tool calls (it needs data) or text (it has an answer). If tool calls: the agent executes each tool, appends results to the conversation, and calls the LLM again with the expanded context. This loops until the LLM gives a text answer or we hit the 5-iteration cap. At the cap, we force an answer by calling the LLM without tool access."

### Q2: How do you prevent infinite loops in the agent?
**A:** "Three safeguards. First, `max_iterations=5` — the for-loop runs at most 5 times. Second, after 5 iterations, we append 'Please provide your best answer' and call the LLM with `tools=None` — it's forced to give text, not more tool calls. Third, `temperature=0.3` reduces randomness, making the LLM less likely to keep calling the same tool in a loop."

### Q3: What happens if a tool execution fails?
**A:** "The tool call is wrapped in try/except. On error, the result becomes `'Tool error: {message}'` instead of crashing. This error text is fed back to the LLM, which can decide to try a different tool or answer with a caveat: 'I couldn't fetch your sleep data, but based on what I know...' The agent never crashes because of a tool failure."

### Q4: How is this different from LangChain's AgentExecutor?
**A:** "Same algorithm, simpler implementation. LangChain's AgentExecutor does the same Think→Act→Observe loop but adds abstractions: OutputParsers, AgentActionMessage types, callback handlers, streaming middleware. Our implementation is ~100 lines of direct Python — the LLM returns tool calls, we execute them, feed results back. Both produce the same behavior. Ours is for learning and understanding; LangChain's is for production with its ecosystem."

### Q5: Why temperature 0.3 for agent reasoning but 0.7 for chat?
**A:** "Agent reasoning requires precision. When the LLM decides which tool to call and what arguments to pass, it needs to be reliable — `query_logs` with `days=7`, not a creative variation. Temperature 0.3 gives consistent, focused outputs. For the final answer text, we could use higher temperature for more natural language, but 0.3 keeps the response data-focused. In pure chat mode (no tools), we use 0.7 for a more conversational tone."

### Q6: How does the message list grow during execution?
**A:** "It accumulates. Start: [system, user_message] (2 messages). After tool call 1: [system, user, assistant_'checking...', tool_result] (4 messages). After tool call 2: [system, user, assistant, tool1, assistant, tool2] (6 messages). After tool call 3: 8 messages. The LLM sees the FULL conversation including all tool results — this is how it builds a comprehensive answer from multiple data sources."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 10b: Agent Memory](./phase4-part10b-ai-agent-memory.md) |
| ➡️ Next | [Phase 4 Part 10d: Agent Connections & Flows](./phase4-part10d-ai-agent-connections-and-flows.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Agent Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 10a | ✅ Done | Agent Tools |
| 10b | ✅ Done | Agent Memory |
| **10c** | ✅ **You are here** | ReAct Loop ★★★ |
| 10d | ⬜ Next | Agent Connections & Flows |

---

**End of Phase 4 Part 10c: ReAct Loop ★★★**

*This is the most important AI file in the project. ~100 lines that implement Think → Act → Observe → Answer. If you can explain this loop in an interview, you understand how modern AI agents work — from LangChain to CrewAI to OpenAI Assistants. Next: flow diagrams connecting everything in the Agents layer.*
