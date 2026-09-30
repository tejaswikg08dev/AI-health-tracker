# ============================================================================
# LLM — OpenAI Client (PAID, Production)
# ============================================================================
# WHAT THIS FILE DOES:
#   Calls the OpenAI API (GPT-4, GPT-3.5-turbo).
#   This is what companies use in production.
#   You won't use this during development (use Ollama/Groq instead).
#
# WHY INCLUDE IT:
#   1. Shows you know the production pattern
#   2. The code is nearly identical to GroqClient (same API format)
#   3. In interviews: "My system supports Ollama, Groq, and OpenAI via
#      the Strategy pattern — switching is a config change"
#
# COST: $0.002-$0.06 per 1K tokens (GPT-3.5 to GPT-4)
#   For learning: don't use this. For production: company pays.
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

OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAIClient(BaseLLMClient):
    """
    OpenAI LLM client — production-grade AI.

    Same API format as Groq (both are OpenAI-compatible).
    The factory pattern means the rest of the app doesn't know
    or care which provider is being used.
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL if "gpt" in settings.LLM_MODEL else "gpt-3.5-turbo"
        self.embedding_model = "text-embedding-3-small"
        self.http_client = httpx.AsyncClient(
            base_url=OPENAI_BASE_URL,
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
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
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
            logger.error("openai_api_error", status=e.response.status_code)
            return LLMResponse(content="AI service error. Please try again.", model=self.model)
        except Exception as e:
            logger.error("openai_chat_error", error=str(e))
            return LLMResponse(content=f"Error: {str(e)}", model=self.model)

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
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
                    data_str = line[6:]
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
        """Generate embeddings using OpenAI's embedding API."""
        try:
            response = await self.http_client.post(
                "/embeddings",
                json={
                    "model": self.embedding_model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            data = response.json()

            # OpenAI returns embeddings in the same order as inputs
            return [item["embedding"] for item in data["data"]]

        except Exception as e:
            logger.error("openai_embed_error", error=str(e))
            return [[0.0] * 1536 for _ in texts]
