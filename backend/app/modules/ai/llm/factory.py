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
