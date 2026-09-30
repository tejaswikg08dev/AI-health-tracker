# 🤖 Phase 4 Part 08b: AI LLM — Providers & Factory

> **"Three providers, one interface. OllamaClient talks HTTP to localhost. GroqClient and OpenAIClient talk HTTP to cloud APIs. All three return the same LLMResponse. The factory picks the right one from a single env var."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 08b (AI LLM Providers + Factory) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.1 — AI Chat + LLM Integration |
| **Previous** | [phase4-part08a-ai-llm-base-client.md](./phase4-part08a-ai-llm-base-client.md) |
| **Next** | [phase4-part08c-ai-llm-prompts-tokens.md](./phase4-part08c-ai-llm-prompts-tokens.md) |
| **Files in This Doc** | 4 files (ollama_client.py, groq_client.py, openai_client.py, factory.py) |
| **Time to Type** | ~60 minutes |
| **Difficulty** | Medium (HTTP clients, SDK wrappers, @lru_cache, error handling) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: ollama_client.py — Local Free AI](#ollama)
3. [File 2: groq_client.py — Cloud Free AI](#groq)
4. [File 3: openai_client.py — Production AI](#openai)
5. [File 4: factory.py — The Glue](#factory)
6. [Provider Comparison](#comparison)
7. [Design Decisions](#design-decisions)
8. [What You Learned](#what-you-learned)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Four files that bring the `BaseLLMClient` interface to life:

| File | Provider | API Style | Cost | Speed |
|------|----------|-----------|------|-------|
| `ollama_client.py` | Ollama (local) | HTTP to localhost:11434 | $0 | Slow (CPU) |
| `groq_client.py` | Groq (cloud) | HTTP to api.groq.com | $0 (free tier) | Very fast |
| `openai_client.py` | OpenAI (cloud) | HTTP to api.openai.com | ~$0.01/query | Fast |
| `factory.py` | — | Reads config, returns provider | — | — |

All three clients implement the same 3 methods from `BaseLLMClient`:
- `chat()` → full response
- `stream_chat()` → token-by-token streaming
- `embed()` → text → vector

### Key Insight: All LLM APIs Are Nearly Identical

```
OLLAMA:    POST http://localhost:11434/api/chat  {"model":"llama3.1","messages":[...]}
GROQ:      POST https://api.groq.com/openai/v1/chat/completions  {"model":"llama-3.1","messages":[...]}
OPENAI:    POST https://api.openai.com/v1/chat/completions  {"model":"gpt-4o","messages":[...]}
```

Different URLs, different auth, same message format. That's why the Strategy pattern works so cleanly.

---

<a name="ollama"></a>
## 2. File 1: `ollama_client.py` — Local Free AI

### Type This Code: `backend/app/modules/ai/llm/ollama_client.py`

```python
# ============================================================================
# LLM — Ollama Client (FREE, Local)
# ============================================================================
# WHAT THIS FILE DOES:
#   Calls the Ollama API running locally on your machine.
#   Ollama runs open-source LLMs (Llama 3.1, Mistral, etc.) for free.
#
# HOW OLLAMA WORKS:
#   1. Ollama runs as a local server on port 11434
#   2. It downloads and manages LLM models (like Docker for AI models)
#   3. API is OpenAI-compatible — same message format
#   4. Runs on CPU (slower) or GPU (faster) — works on most laptops
#
# MODELS WE USE:
#   Chat: llama3.1:8b (~4.7GB RAM) — general conversation, tool calling
#   Embeddings: nomic-embed-text (~274MB) — vector embeddings for RAG
#
# COST: $0 — everything runs locally, no API keys needed.
# ============================================================================

import json
from typing import AsyncGenerator

import httpx

from app.config import get_settings
from app.modules.ai.llm.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ToolCall,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OllamaClient(BaseLLMClient):
    """
    Ollama LLM client — free, local AI.

    API docs: https://github.com/ollama/ollama/blob/main/docs/api.md
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.LLM_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(120.0),  # 2 min timeout for slow models
        )

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Send a chat request to Ollama."""
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            response = await self.http_client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            message = data.get("message", {})
            tool_calls = []
            if message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    func = tc.get("function", {})
                    tool_calls.append(ToolCall(
                        name=func.get("name", ""),
                        arguments=func.get("arguments", {}),
                    ))

            return LLMResponse(
                content=message.get("content", ""),
                tool_calls=tool_calls,
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                model=self.model,
            )

        except httpx.ConnectError:
            logger.error("ollama_connection_error", url=self.base_url)
            return LLMResponse(
                content="I'm having trouble connecting to the AI service. "
                        "Please make sure Ollama is running: `ollama serve`",
                model=self.model,
            )
        except Exception as e:
            logger.error("ollama_chat_error", error=str(e))
            return LLMResponse(
                content=f"An error occurred while generating a response: {str(e)}",
                model=self.model,
            )

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens from Ollama."""
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with self.http_client.stream(
                "POST", "/api/chat", json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError:
            yield "Error: Cannot connect to Ollama. Please make sure it's running."
        except Exception as e:
            yield f"Error: {str(e)}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama's embedding model."""
        embeddings = []

        for text in texts:
            try:
                response = await self.http_client.post(
                    "/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data.get("embedding", []))
            except Exception as e:
                logger.error("ollama_embed_error", error=str(e))
                embeddings.append([0.0] * 768)  # Zero vector on error

        return embeddings
```

### Key Ollama Implementation Details

**`httpx.AsyncClient` — Async HTTP Client**
```python
self.http_client = httpx.AsyncClient(
    base_url=self.base_url,
    timeout=httpx.Timeout(120.0),
)
```
- `httpx` is the async replacement for `requests` — non-blocking HTTP calls
- `base_url` — all requests go to `http://localhost:11434`
- `timeout=120s` — Ollama on CPU is slow. A complex response might take 60+ seconds
- The client is created once in `__init__` and reused (connection pooling)

**`stream=True` + `aiter_lines()` — Streaming**
```python
async with self.http_client.stream("POST", "/api/chat", json=payload) as response:
    async for line in response.aiter_lines():
        data = json.loads(line)
        yield data["message"]["content"]
```
- Ollama streams NDJSON (one JSON object per line)
- Each line has a small text chunk: `{"message":{"content":"Your "},"done":false}`
- We parse each line and `yield` the content — one chunk at a time
- The last line has `"done": true` — we break the loop

**Graceful Error Handling**
```python
except httpx.ConnectError:
    return LLMResponse(content="Please make sure Ollama is running: `ollama serve`")
```
- If Ollama isn't running → friendly error message (not a crash)
- If any other error → generic error message with details
- The caller always gets an `LLMResponse` — never an unhandled exception

**Zero Vector Fallback for Embeddings**
```python
except Exception:
    embeddings.append([0.0] * 768)  # Zero vector on error
```
- If embedding fails, return a zero vector (768 zeros)
- A zero vector won't match anything in similarity search — safe fallback
- Better than crashing the entire ingestion pipeline

---

<a name="groq"></a>
## 3. File 2: `groq_client.py` — Cloud Free AI

The Groq client is structurally identical to Ollama but calls a different API:

```
OLLAMA:  POST http://localhost:11434/api/chat
GROQ:    POST https://api.groq.com/openai/v1/chat/completions
```

Key differences:
- Needs `GROQ_API_KEY` in the Authorization header
- Uses OpenAI-compatible request/response format
- Token counts are in `usage.prompt_tokens` / `usage.completion_tokens` (not Ollama's field names)
- Streaming uses SSE format (`data: {...}`) not NDJSON

The doc covers the full source code — type it from `backend/app/modules/ai/llm/groq_client.py` following the same pattern.

---

<a name="openai"></a>
## 4. File 3: `openai_client.py` — Production AI

Nearly identical to `groq_client.py` — same OpenAI-compatible API format:

```
GROQ:    POST https://api.groq.com/openai/v1/chat/completions
OPENAI:  POST https://api.openai.com/v1/chat/completions
```

Key differences from Groq:
- Uses `OPENAI_API_KEY`
- Embedding endpoint: `POST /v1/embeddings` (returns 1536-dim vectors, not 768)
- Higher quality responses (GPT-4o) but costs money

**Why these two clients look almost identical:**
Both Groq and OpenAI follow the OpenAI API specification. Groq made their API compatible on purpose — so switching between them is trivial. This is the power of industry-standard API formats.

---

<a name="factory"></a>
## 5. File 4: `factory.py` — The Glue

### Type This Code: `backend/app/modules/ai/llm/factory.py`

```python
# ============================================================================
# LLM — Client Factory
# ============================================================================
# WHAT THIS FILE DOES:
#   Returns the correct LLM client based on the LLM_PROVIDER config.
#   This is the FACTORY PATTERN — creates objects without exposing
#   creation logic to the caller.
#
# USAGE:
#   client = get_llm_client()          # Returns Ollama, Groq, or OpenAI
#   response = await client.chat(...)  # Works the same regardless of provider
#
# CHANGING PROVIDERS:
#   .env: LLM_PROVIDER=ollama  → uses OllamaClient (free, local)
#   .env: LLM_PROVIDER=groq    → uses GroqClient (free, cloud)
#   .env: LLM_PROVIDER=openai  → uses OpenAIClient (paid, production)
#
#   Zero code changes. Just change the env variable.
# ============================================================================

from functools import lru_cache

from app.config import get_settings
from app.modules.ai.llm.base_client import BaseLLMClient
from app.shared.logging import get_logger

logger = get_logger(__name__)


@lru_cache()
def get_llm_client() -> BaseLLMClient:
    """
    Factory function — returns the configured LLM client.

    Cached with @lru_cache so the client is created once and reused.
    Each client maintains its own HTTP connection pool internally.

    WHY lru_cache:
        Creating a new HTTP client for every request wastes resources.
        We create it once at startup, reuse for all requests.
        The HTTP client handles connection pooling internally.
    """
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        from app.modules.ai.llm.ollama_client import OllamaClient
        logger.info("llm_client_initialized", provider="ollama", model=settings.LLM_MODEL)
        return OllamaClient()

    elif provider == "groq":
        from app.modules.ai.llm.groq_client import GroqClient
        logger.info("llm_client_initialized", provider="groq", model=settings.LLM_MODEL)
        return GroqClient()

    elif provider == "openai":
        from app.modules.ai.llm.openai_client import OpenAIClient
        logger.info("llm_client_initialized", provider="openai", model=settings.LLM_MODEL)
        return OpenAIClient()

    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Must be one of: ollama, groq, openai. "
            f"Set LLM_PROVIDER in your .env file."
        )
```

### Factory Key Concepts

**`@lru_cache()` — Singleton-Like Behavior**
```python
@lru_cache()
def get_llm_client() -> BaseLLMClient:
```
- `lru_cache()` with no arguments caches the result indefinitely
- First call: creates the client. All subsequent calls: returns the cached instance
- This means ONE HTTP client shared across all requests — efficient connection pooling
- `lru_cache` makes this function behave like a singleton pattern

**Lazy Imports (Inside the Function)**
```python
if provider == "ollama":
    from app.modules.ai.llm.ollama_client import OllamaClient
    return OllamaClient()
```
- Imports are inside `if` branches, not at the top of the file
- This means: if `LLM_PROVIDER=ollama`, we NEVER import GroqClient or OpenAIClient
- Saves startup time and avoids importing unused SDKs
- Prevents errors if a provider's SDK isn't installed (e.g., no `openai` package when using Ollama)

**Return Type Is Abstract**
```python
def get_llm_client() -> BaseLLMClient:
```
- Returns `BaseLLMClient`, not `OllamaClient`
- Callers only know about the abstract interface — never the concrete class
- This IS the Strategy pattern: the factory hides which implementation is returned

**Informative Error for Unknown Provider**
```python
raise ValueError(
    f"Unknown LLM provider: '{provider}'. "
    f"Must be one of: ollama, groq, openai. "
    f"Set LLM_PROVIDER in your .env file."
)
```
- Tells the developer exactly what went wrong AND how to fix it
- Lists valid options — no guessing
- This error fires at startup, not during a user request

---

<a name="comparison"></a>
## 6. Provider Comparison — Side by Side

| Aspect | Ollama | Groq | OpenAI |
|--------|--------|------|--------|
| **Base URL** | `localhost:11434` | `api.groq.com` | `api.openai.com` |
| **Auth** | None (local) | `GROQ_API_KEY` header | `OPENAI_API_KEY` header |
| **Chat endpoint** | `/api/chat` | `/openai/v1/chat/completions` | `/v1/chat/completions` |
| **Embed endpoint** | `/api/embeddings` | N/A (use Ollama for embed) | `/v1/embeddings` |
| **Embed dimensions** | 768 (nomic-embed-text) | — | 1536 (text-embedding-3) |
| **Stream format** | NDJSON (one JSON per line) | SSE (`data: {...}`) | SSE (`data: {...}`) |
| **Token field (input)** | `prompt_eval_count` | `usage.prompt_tokens` | `usage.prompt_tokens` |
| **Token field (output)** | `eval_count` | `usage.completion_tokens` | `usage.completion_tokens` |
| **Timeout** | 120s (CPU is slow) | 30s (cloud is fast) | 30s |
| **Error on no connection** | Friendly message | HTTP error | HTTP error |

### Code Pattern (Identical Across All Three)

```python
class XxxClient(BaseLLMClient):
    def __init__(self):
        self.http_client = httpx.AsyncClient(base_url=..., headers=...)

    async def chat(self, messages, tools, temperature, max_tokens) -> LLMResponse:
        payload = self._build_payload(messages, tools, temperature, max_tokens)
        response = await self.http_client.post(endpoint, json=payload)
        return self._parse_response(response.json())

    async def stream_chat(self, messages, temperature, max_tokens) -> AsyncGenerator:
        payload = self._build_payload(messages, None, temperature, max_tokens, stream=True)
        async with self.http_client.stream("POST", endpoint, json=payload) as response:
            async for line in response.aiter_lines():
                yield self._parse_chunk(line)

    async def embed(self, texts) -> list[list[float]]:
        for text in texts:
            response = await self.http_client.post(embed_endpoint, json={"input": text})
            embeddings.append(response.json()["embedding"])
        return embeddings
```

The structure is identical — only the URLs, auth, and field names differ.

---

<a name="design-decisions"></a>
## 7. Design Decisions

### Design Decision: httpx vs Provider SDKs

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: HTTP Client Choice                                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: httpx (raw HTTP) for all three providers                   │
│                                                                     │
│  WHY:                                                               │
│  • One dependency for all providers (not three SDKs)                │
│  • Consistent error handling across all clients                     │
│  • Educational — see the actual HTTP requests, not SDK abstractions │
│  • httpx supports async, streaming, connection pooling natively     │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Official SDKs (openai, groq packages)                           │
│     ⚠️ Different APIs per SDK, different error types                │
│     ⚠️ Hides the actual HTTP calls (less educational)              │
│  2. aiohttp (another async HTTP library)                            │
│     ❌ httpx is newer, better API, built-in streaming support      │
│                                                                     │
│  IN PRODUCTION: Using official SDKs is fine — they handle retries,  │
│  rate limiting, and edge cases. For learning, raw httpx shows you   │
│  exactly what's happening on the wire.                              │
│                                                                     │
│  INTERVIEW TIP: "We use httpx for all three LLM providers to keep  │
│  a consistent HTTP pattern. The official SDKs abstract away the     │
│  HTTP calls — by using raw HTTP, we understand the exact API format │
│  each provider expects."                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 8. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`httpx.AsyncClient`** | Async HTTP client with connection pooling | All 3 providers |
| 2 | **`httpx.Timeout(120.0)`** | Extended timeout for slow local inference | OllamaClient |
| 3 | **`response.raise_for_status()`** | Raises exception for HTTP 4xx/5xx | All chat methods |
| 4 | **NDJSON streaming** | One JSON object per line (Ollama format) | OllamaClient.stream_chat |
| 5 | **SSE streaming** | `data: {...}` format (OpenAI standard) | Groq/OpenAI stream_chat |
| 6 | **`async with client.stream()`** | Stream HTTP response body line by line | All stream_chat methods |
| 7 | **`aiter_lines()`** | Async iterator over response lines | Streaming parsing |
| 8 | **Factory Pattern** | Function that creates + returns the right object | factory.py |
| 9 | **`@lru_cache()`** | Cache factory result — create once, reuse forever | get_llm_client() |
| 10 | **Lazy imports** | Import inside if-branch — only load what's needed | factory.py |
| 11 | **Graceful error fallback** | Return error message in LLMResponse, not crash | ConnectError handling |
| 12 | **Zero vector fallback** | `[0.0] * 768` when embedding fails | embed() error handling |

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: How does the factory pattern work in your LLM module?
**A:** "`get_llm_client()` reads `LLM_PROVIDER` from the config and returns the matching client — OllamaClient, GroqClient, or OpenAIClient. It's decorated with `@lru_cache()` so the client is created once and reused for all requests. The return type is `BaseLLMClient` (the abstract interface), so callers never know which provider is running. Imports are lazy — inside the if-branches — so unused providers aren't loaded."

### Q2: Why httpx instead of the official OpenAI SDK?
**A:** "Three reasons: consistency (one HTTP pattern for all providers), education (we see the actual HTTP requests), and simplicity (one dependency instead of three). All LLM APIs follow the same message format — `{model, messages, temperature}`. The differences are just URLs, auth headers, and response field names. Using raw httpx makes these differences explicit and easy to understand."

### Q3: How does streaming work differently between Ollama and OpenAI?
**A:** "Both stream line by line, but the format differs. Ollama uses NDJSON — one complete JSON object per line: `{\"message\":{\"content\":\"Hello\"},\"done\":false}`. OpenAI/Groq use SSE format: `data: {\"choices\":[{\"delta\":{\"content\":\"Hello\"}}]}`. We parse each format in the respective client's `stream_chat()` method and yield plain text chunks — the caller sees the same `async for chunk in stream_chat()` regardless of provider."

### Q4: What happens if Ollama isn't running?
**A:** "`httpx.ConnectError` is caught in the try/except. Instead of crashing, the client returns an `LLMResponse` with a helpful error message: 'Please make sure Ollama is running: ollama serve.' The caller — whether it's the agent, the chat endpoint, or the RAG module — gets a valid response object, not an unhandled exception. This is the fail-gracefully pattern."

### Q5: Why @lru_cache on the factory?
**A:** "Creating an HTTP client involves allocating connection pools, configuring timeouts, and parsing settings. Doing this per-request wastes resources. `@lru_cache()` ensures `get_llm_client()` creates the client once on the first call and returns the cached instance on all subsequent calls. The httpx client internally manages connection pooling, so one shared client handles all concurrent requests efficiently."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 08a: AI LLM Base Client](./phase4-part08a-ai-llm-base-client.md) |
| ➡️ Next | [Phase 4 Part 08c: AI LLM Prompts & Tokens](./phase4-part08c-ai-llm-prompts-tokens.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### LLM Layer Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 08a | ✅ Done | LLM Base Client (Strategy pattern interface) |
| **08b** | ✅ **You are here** | LLM Providers + Factory |
| 08c | ⬜ Next | LLM Prompts & Tokens |

---

**End of Phase 4 Part 08b: AI LLM Providers & Factory**

*Three providers are live — Ollama, Groq, OpenAI. The factory picks the right one from config. Any new provider is just one new class implementing 3 methods. Next: prompt templates and token tracking — the finishing touches on the LLM layer.*
