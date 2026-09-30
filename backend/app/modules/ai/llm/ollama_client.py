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

    Ollama's API is similar to OpenAI's, making it easy to swap providers.
    The main differences:
    - Base URL is localhost:11434 (not api.openai.com)
    - Tool calling support depends on the model
    - No API key needed (it's local)
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.LLM_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL
        # httpx client with extended timeout (LLM inference can be slow locally)
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
        """
        Send a chat request to Ollama.

        Ollama API endpoint: POST /api/chat
        Request format is similar to OpenAI's chat/completions.
        """
        # Build request payload
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,               # Get complete response at once
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,  # Ollama's name for max_tokens
            },
        }

        # Add tools if provided (for agent mode)
        if tools:
            payload["tools"] = tools

        try:
            response = await self.http_client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse response
            message = data.get("message", {})

            # Check for tool calls
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
        """
        Stream response tokens from Ollama.

        Ollama streams JSON objects, one per line.
        Each object has a "message.content" field with a few tokens.
        The last object has "done": true.
        """
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
        """
        Generate embeddings using Ollama's embedding model.

        Ollama API endpoint: POST /api/embed (batch) or /api/embeddings (single)
        We use /api/embed for batch processing.
        """
        embeddings = []

        for text in texts:
            try:
                response = await self.http_client.post(
                    "/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": text,
                    },
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data.get("embedding", []))

            except Exception as e:
                logger.error("ollama_embed_error", error=str(e))
                # Return zero vector on error (won't match anything in search)
                embeddings.append([0.0] * 768)

        return embeddings
