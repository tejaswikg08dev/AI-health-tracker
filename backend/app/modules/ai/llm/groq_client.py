# ============================================================================
# LLM — Groq Client (FREE, Cloud, Fast)
# ============================================================================
# WHAT THIS FILE DOES:
#   Calls the Groq API — a free, ultra-fast LLM inference service.
#   Groq uses custom LPU (Language Processing Unit) hardware for speed.
#
# WHY GROQ:
#   - Free tier: 30 requests/min, 14,400 requests/day
#   - Extremely fast: ~500 tokens/second (10x faster than OpenAI)
#   - OpenAI-compatible API — same request/response format
#   - Runs Llama 3.1, Mixtral, and other open models
#
# WHEN TO USE:
#   - Deployed staging environment (can't run Ollama on Render/Vercel)
#   - When you need fast responses for demo
#   - As backup when Ollama is slow on CPU-only machines
#
# COST: $0 (free tier is generous for a personal project)
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

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqClient(BaseLLMClient):
    """
    Groq LLM client — free cloud inference.

    Uses the OpenAI-compatible API format.
    The only difference from OpenAI: different base URL and API key.
    This is why the abstract interface pattern is so powerful —
    both clients have nearly identical implementations.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.LLM_MODEL if "llama" in settings.LLM_MODEL else "llama-3.1-8b-instant"
        self.http_client = httpx.AsyncClient(
            base_url=GROQ_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0),
        )

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Send a chat request to Groq's OpenAI-compatible API."""
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = await self.http_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            message = choice["message"]
            usage = data.get("usage", {})

            # Parse tool calls
            tool_calls = []
            if message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    func = tc.get("function", {})
                    args = func.get("arguments", "{}")
                    if isinstance(args, str):
                        args = json.loads(args)
                    tool_calls.append(ToolCall(
                        name=func.get("name", ""),
                        arguments=args,
                    ))

            return LLMResponse(
                content=message.get("content", "") or "",
                tool_calls=tool_calls,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=self.model,
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("groq_rate_limited")
                return LLMResponse(
                    content="I'm temporarily rate-limited. Please try again in a moment.",
                    model=self.model,
                )
            logger.error("groq_api_error", status=e.response.status_code)
            return LLMResponse(
                content="An error occurred with the AI service. Please try again.",
                model=self.model,
            )
        except Exception as e:
            logger.error("groq_chat_error", error=str(e))
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
            )

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens from Groq."""
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with self.http_client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        except Exception as e:
            yield f"Error: {str(e)}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Groq doesn't offer an embedding API.
        Fall back to Ollama for embeddings, or use a placeholder.
        In production, you'd use OpenAI's embedding API.
        """
        logger.warning("groq_no_embeddings", detail="Groq doesn't support embeddings. Using Ollama fallback.")
        # Import Ollama client for embeddings only
        from app.modules.ai.llm.ollama_client import OllamaClient
        ollama = OllamaClient()
        return await ollama.embed(texts)
