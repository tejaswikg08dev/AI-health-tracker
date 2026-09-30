# 🤖 Phase 4 Part 08a: AI LLM — Base Client (Strategy Pattern)

> **"This one file defines the contract that ALL AI providers must follow. Every method, every parameter, every return type. Write this first, and adding Ollama, Groq, OpenAI, or Anthropic is just filling in the blanks."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 08a (AI LLM Base Client) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.1 — AI Chat + LLM Integration |
| **Previous** | [phase4-part08-ai-llm-overview.md](./phase4-part08-ai-llm-overview.md) |
| **Next** | [phase4-part08b-ai-llm-providers.md](./phase4-part08b-ai-llm-providers.md) |
| **Files in This Doc** | 1 file (base_client.py) — 3 data classes + 1 abstract class |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (new concepts: ABC, @abstractmethod, @dataclass, AsyncGenerator) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [Python Concepts Primer](#concepts-primer)
3. [File: base_client.py — Full Source Code](#source)
4. [Line-by-Line Explanation](#line-by-line)
5. [How This Connects to the Rest](#connections)
6. [Design Decisions](#design-decisions)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

One file with four classes:

| Class | Type | What It Does |
|-------|------|-------------|
| `LLMMessage` | `@dataclass` | A single message in a conversation (role + content) |
| `ToolCall` | `@dataclass` | A tool the LLM wants to call (name + arguments) |
| `LLMResponse` | `@dataclass` | The LLM's response (text or tool calls + token counts) |
| `BaseLLMClient` | `ABC` | Abstract interface — 3 methods every provider MUST implement |

These are the **building blocks** used everywhere in the AI module:
- Agent sends `list[LLMMessage]` to the LLM
- LLM returns `LLMResponse` (with text or `ToolCall` list)
- Agent executes the tool and adds the result as another `LLMMessage`

---

<a name="concepts-primer"></a>
## 2. Python Concepts Primer

### What Is `@dataclass`?

A **dataclass** is Python's shorthand for creating classes that mainly hold data:

```python
# WITHOUT @dataclass (verbose):
class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

# WITH @dataclass (concise):
@dataclass
class LLMMessage:
    role: str
    content: str

# Both produce the same result:
msg = LLMMessage(role="user", content="How's my sleep?")
print(msg.role)     # "user"
print(msg.content)  # "How's my sleep?"
```

`@dataclass` auto-generates `__init__`, `__repr__`, and `__eq__` — you don't write boilerplate.

### What Is `ABC` and `@abstractmethod`?

**ABC** (Abstract Base Class) defines a **contract** — methods that subclasses MUST implement:

```python
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(self, messages) -> LLMResponse:
        ...  # No implementation here

# This FAILS — can't instantiate abstract class:
client = BaseLLMClient()  # ❌ TypeError!

# This WORKS — OllamaClient implements all abstract methods:
class OllamaClient(BaseLLMClient):
    async def chat(self, messages) -> LLMResponse:
        # Real implementation here
        return LLMResponse(content="Hello!")

client = OllamaClient()  # ✅ Works!
```

If you forget to implement an abstract method, Python crashes at instantiation time — not at runtime. This catches errors early.

### What Is `AsyncGenerator`?

An **async generator** yields values one at a time, asynchronously:

```python
async def stream_chat(self) -> AsyncGenerator[str, None]:
    yield "Your "      # Pause, send this chunk
    yield "sleep "     # Pause, send this chunk
    yield "averaged "  # Pause, send this chunk
    yield "6.8 hours." # Done

# Usage:
async for chunk in client.stream_chat(messages):
    print(chunk, end="")  # Prints word by word: "Your sleep averaged 6.8 hours."
```

This is how streaming works — the LLM generates tokens one at a time, and we yield each chunk to the frontend via SSE.

---

<a name="source"></a>
## 3. File: `base_client.py` — Full Source Code

### Type This Code: `backend/app/modules/ai/llm/base_client.py`

```python
# ============================================================================
# LLM — Abstract Base Client
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the INTERFACE that all LLM providers must implement.
#   Ollama, Groq, and OpenAI all look the same to the rest of the app.
#
# WHY AN ABSTRACT CLASS:
#   This is the STRATEGY PATTERN — a core design pattern.
#
#   Without it:
#     if provider == "ollama": call_ollama(...)
#     elif provider == "groq": call_groq(...)
#     elif provider == "openai": call_openai(...)
#     # Every function that uses AI has these if/elif chains — nightmare
#
#   With it:
#     client = get_llm_client()   # Returns the right one based on config
#     response = await client.chat(messages)  # Works with ANY provider
#     # Adding a new provider = one new class, zero changes elsewhere
#
# THIS IS EXACTLY HOW COMPANIES DO IT:
#   - Same interface for OpenAI, Anthropic, AWS Bedrock, Azure OpenAI
#   - Swap providers via config, not code changes
#   - Test with a mock client (no API calls, deterministic responses)
#
# INTERVIEW NOTE:
#   "How would you design an AI system that works with multiple LLM providers?"
#   Answer: "Strategy pattern with an abstract base class. Each provider
#   implements the same interface. A factory function returns the right
#   implementation based on configuration."
# ============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class LLMMessage:
    """
    A single message in a conversation.

    Mirrors the OpenAI/Anthropic message format — the industry standard.
    Every LLM API uses role + content, so this works universally.

    Roles:
        system    → instructions for the AI (persona, rules, context)
        user      → the human's message
        assistant → the AI's response
        tool      → result of a tool call (for agents)
    """

    role: str       # "system", "user", "assistant", "tool"
    content: str    # The message text


@dataclass
class ToolCall:
    """
    A tool call requested by the LLM (for agent mode).

    When the LLM decides to use a tool, it returns a ToolCall
    instead of a text response. The agent executes the tool
    and feeds the result back to the LLM.
    """

    name: str                       # Tool name (e.g., "query_logs")
    arguments: dict = field(default_factory=dict)  # Tool arguments as key-value pairs


@dataclass
class LLMResponse:
    """
    Response from an LLM API call.

    Either:
    - content is filled (text response) and tool_calls is empty
    - tool_calls is filled (agent wants to use tools) and content may be empty

    Never both — the LLM either responds with text OR requests tool calls.
    """

    content: str = ""                                # Text response
    tool_calls: list[ToolCall] = field(default_factory=list)  # Requested tool calls
    input_tokens: int = 0                            # Tokens in the prompt
    output_tokens: int = 0                           # Tokens in the response
    model: str = ""                                  # Model name used

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMClient(ABC):
    """
    Abstract LLM client — all providers implement this interface.

    Methods:
        chat()         → single request/response (for simple queries)
        stream_chat()  → streaming response (for real-time chat UI)
        embed()        → generate vector embeddings (for RAG)

    Each provider translates these calls to their specific API format.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Send messages to the LLM and get a complete response.

        Args:
            messages: Conversation history (system + user + assistant messages)
            tools: Tool definitions for agent mode (None for simple chat)
            temperature: Randomness (0.0=deterministic, 1.0=creative)
            max_tokens: Maximum response length

        Returns:
            LLMResponse with either content (text) or tool_calls (agent action)
        """
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens one at a time.

        Used by the chat UI — shows the response appearing word by word.
        Each yielded string is a small piece of the response (a few tokens).

        Yields:
            Text chunks as they're generated by the LLM
        """
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate vector embeddings for a list of texts.

        Used by RAG:
        - During ingestion: embed document chunks → store in pgvector
        - During query: embed the user's question → search pgvector

        Args:
            texts: List of strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)
            Dimensions: 768 (nomic-embed-text) or 1536 (OpenAI)
        """
        ...
```

---

<a name="line-by-line"></a>
## 4. Line-by-Line Explanation

### Imports

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator
```

- `ABC` — Abstract Base Class. Any class inheriting from `ABC` can have `@abstractmethod` methods
- `abstractmethod` — decorator that marks a method as "must be implemented by subclasses"
- `dataclass` — decorator that auto-generates `__init__`, `__repr__`, `__eq__`
- `field(default_factory=dict)` — for mutable default values in dataclasses. You can't use `dict` directly as a default because all instances would share the same dict object
- `AsyncGenerator[str, None]` — type hint for async generators. `str` = yield type, `None` = send type (unused)

### `LLMMessage` — The Universal Message Format

```python
@dataclass
class LLMMessage:
    role: str       # "system", "user", "assistant", "tool"
    content: str    # The message text
```

Every LLM API in the world uses this format. A conversation is a list of messages:

```python
messages = [
    LLMMessage(role="system", content="You are a health coach."),
    LLMMessage(role="user", content="How's my sleep?"),
    LLMMessage(role="assistant", content="Your sleep averaged 6.8h..."),
    LLMMessage(role="user", content="What about compared to last week?"),
]
```

The **system** message sets the AI's persona and rules. It's like whispering instructions to an actor before they go on stage.

### `ToolCall` — What the Agent Wants to Do

```python
@dataclass
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)
```

When the LLM decides to use a tool (in agent mode), it doesn't return text — it returns a `ToolCall`:

```python
ToolCall(name="query_logs", arguments={"habit_name": "Sleep", "days": 7})
```

The agent executes this tool, gets the result, and feeds it back to the LLM as a new message.

**Why `field(default_factory=dict)`?**
```python
# BAD — all ToolCall instances share ONE dict:
arguments: dict = {}

# GOOD — each ToolCall gets its OWN empty dict:
arguments: dict = field(default_factory=dict)
```

This is a classic Python gotcha. Mutable defaults (`list`, `dict`, `set`) must use `field(default_factory=...)`.

### `LLMResponse` — What Comes Back

```python
@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0
```

Two modes:
- **Text response:** `content="Your sleep averaged 6.8h..."`, `tool_calls=[]`
- **Tool request:** `content=""`, `tool_calls=[ToolCall(name="query_logs", ...)]`

`@property` makes methods look like attributes: `response.total_tokens` (no parentheses).

Token counts are essential for cost tracking: `total_tokens × price_per_token = cost`.

### `BaseLLMClient` — The Abstract Interface

```python
class BaseLLMClient(ABC):

    @abstractmethod
    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=1024) -> LLMResponse:
        ...

    @abstractmethod
    async def stream_chat(self, messages, temperature=0.7, max_tokens=1024) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...
```

Three methods every provider MUST implement:

| Method | Purpose | Used By |
|--------|---------|---------|
| `chat()` | Full request/response | Agent reasoning, simple Q&A, insight generation |
| `stream_chat()` | Token-by-token streaming | Chat UI (SSE endpoint) |
| `embed()` | Text → vector | RAG (ingestion + query) |

**`temperature` parameter:**
- `0.0` = deterministic (same input → same output). Used for data analysis
- `0.7` = balanced (some creativity). Default for chat
- `1.0` = creative (more random). Used for brainstorming

**`max_tokens` parameter:**
- Limits response length. 1024 tokens ≈ ~750 words
- Prevents runaway responses (LLM generating 10,000 words)
- Each token costs money with OpenAI

**`...` (Ellipsis) in abstract methods:**
- In Python, `...` is valid as a method body — it means "no implementation"
- `pass` also works, but `...` is the convention for abstract methods
- The real implementation is in OllamaClient, GroqClient, OpenAIClient

---

<a name="connections"></a>
## 5. How This Connects to the Rest

```
base_client.py (this file)
  │
  │ defines the interface
  │
  ├── ollama_client.py    implements chat(), stream_chat(), embed()
  ├── groq_client.py      implements chat(), stream_chat(), embed()
  ├── openai_client.py    implements chat(), stream_chat(), embed()
  │
  │ factory returns one of them
  │
  ├── factory.py          get_llm_client() → reads config → returns provider
  │
  │ used by
  │
  ├── agents/base_agent.py    calls client.chat(messages, tools=...)
  ├── rag/embeddings.py       calls client.embed(texts)
  ├── rag/retriever.py        calls client.embed([query])
  ├── service.py              calls client.chat() or client.stream_chat()
  └── router.py               wraps stream_chat() in SSE StreamingResponse
```

**The rest of the codebase only sees `BaseLLMClient`** — never OllamaClient, GroqClient, or OpenAIClient directly. This is the Strategy pattern in action.

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision: Three Methods, Not Ten

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Interface Size                                    │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: 3 methods (chat, stream_chat, embed)                       │
│                                                                     │
│  WHY NOT MORE:                                                      │
│  • Every new method must be implemented by EVERY provider            │
│  • 3 methods × 3 providers = 9 implementations (manageable)         │
│  • 10 methods × 3 providers = 30 implementations (burden)           │
│                                                                     │
│  WHY THESE 3:                                                       │
│  • chat() — core: every AI feature needs this                       │
│  • stream_chat() — UX: real-time chat needs streaming               │
│  • embed() — RAG: document search needs embeddings                  │
│                                                                     │
│  MISSING (intentionally):                                           │
│  • image generation — not needed for health tracking                 │
│  • fine-tuning — out of scope                                       │
│  • function calling (native) — we use our own ReAct loop instead    │
│                                                                     │
│  INTERVIEW TIP: "We kept the interface to 3 methods to minimize     │
│  the implementation burden for each provider. Every additional       │
│  method means N more implementations. chat(), stream_chat(), and    │
│  embed() cover all our use cases."                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`@dataclass`** | Auto-generates `__init__`, `__repr__`, `__eq__` | LLMMessage, ToolCall, LLMResponse |
| 2 | **`field(default_factory=...)`** | Mutable defaults for dataclasses (avoids shared state) | ToolCall.arguments, LLMResponse.tool_calls |
| 3 | **`ABC` (Abstract Base Class)** | Cannot be instantiated — forces subclasses to implement methods | BaseLLMClient |
| 4 | **`@abstractmethod`** | Marks a method that subclasses MUST implement | chat, stream_chat, embed |
| 5 | **`...` (Ellipsis)** | "No implementation" body for abstract methods | All abstract methods |
| 6 | **Strategy Pattern** | One interface, multiple implementations, swap via config | BaseLLMClient hierarchy |
| 7 | **`@property`** | Method that behaves like an attribute (no parentheses) | total_tokens, has_tool_calls |
| 8 | **`AsyncGenerator[str, None]`** | Type hint for async generators (yield str, no send) | stream_chat return type |
| 9 | **Message roles** | system, user, assistant, tool — universal LLM format | LLMMessage.role |
| 10 | **Temperature** | 0.0=deterministic, 0.7=balanced, 1.0=creative | chat/stream_chat parameter |
| 11 | **Token counting** | input_tokens + output_tokens = cost tracking | LLMResponse |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: What is the Strategy pattern and how do you use it?
**A:** "The Strategy pattern defines a family of algorithms behind a common interface, making them interchangeable. Our `BaseLLMClient` is the abstract interface with three methods: `chat()`, `stream_chat()`, and `embed()`. Three concrete classes — OllamaClient, GroqClient, OpenAIClient — implement this interface for their respective APIs. A factory function reads the config and returns the right one. The rest of the codebase only depends on `BaseLLMClient`, never the concrete implementations. Swapping providers is changing one env var."

### Q2: Why use @dataclass instead of regular classes or Pydantic?
**A:** "Dataclasses are the sweet spot between plain classes and Pydantic for internal data transfer objects. They auto-generate `__init__`, `__repr__`, and `__eq__` without the overhead of Pydantic's validation. We use Pydantic for API schemas (where we need validation) and dataclasses for internal data containers (where we need simplicity and speed). `LLMMessage` and `LLMResponse` are never exposed to the API — they stay within the AI module."

### Q3: Why `field(default_factory=dict)` instead of just `= {}`?
**A:** "Mutable default arguments in Python are shared across ALL instances. If we wrote `arguments: dict = {}`, every ToolCall would share the SAME dict object — modifying one would modify all of them. `field(default_factory=dict)` creates a NEW empty dict for each instance. This is a classic Python gotcha that `@dataclass` handles with `field()`."

### Q4: Why three abstract methods and not more?
**A:** "Every abstract method must be implemented by every provider — 3 methods × 3 providers = 9 implementations. Adding a 4th method means 3 more implementations. We chose the minimum set that covers all use cases: `chat()` for agent reasoning and Q&A, `stream_chat()` for real-time UI, and `embed()` for RAG vector search. Features we don't need (image generation, fine-tuning) aren't in the interface."

### Q5: How does the agent use ToolCall and LLMResponse?
**A:** "The agent sends messages with tool descriptions to the LLM via `chat()`. If the LLM decides to use a tool, `LLMResponse.has_tool_calls` is True and `tool_calls` contains a list of `ToolCall` objects. The agent loops through them, executes each tool, and adds the result as a new `LLMMessage(role='tool', content=result)`. Then it calls `chat()` again with the updated conversation. This continues until the LLM returns a text response (no tool calls) — that's the final answer."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 08: AI LLM Layer Overview](./phase4-part08-ai-llm-overview.md) |
| ➡️ Next | [Phase 4 Part 08b: AI LLM Providers + Factory](./phase4-part08b-ai-llm-providers.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### LLM Layer Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **08a** | ✅ **You are here** | LLM Base Client (Strategy pattern interface) |
| 08b | ⬜ Next | LLM Providers + Factory |
| 08c | ⬜ | LLM Prompts & Tokens |

---

**End of Phase 4 Part 08a: AI LLM Base Client**

*The contract is set — 3 data classes and 1 abstract interface. Every AI provider must implement chat(), stream_chat(), and embed(). Next: the three concrete implementations that bring this interface to life.*
