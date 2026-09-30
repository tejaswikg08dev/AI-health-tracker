# ============================================================================
# RAG — Embedding Generator
# ============================================================================
# WHAT THIS FILE DOES:
#   Converts text into vector embeddings (arrays of numbers).
#   This is step 3 of the RAG ingestion pipeline:
#     Upload → Extract → Chunk → [EMBED] → Store
#
# WHAT ARE EMBEDDINGS:
#   An embedding is a list of 768 or 1536 floating-point numbers
#   that captures the MEANING of a text.
#
#   "I drank 8 glasses of water" → [0.12, -0.45, 0.78, ..., 0.33]
#   "My water intake was 8 cups" → [0.11, -0.44, 0.79, ..., 0.34]
#   "The weather is sunny today" → [0.89, 0.23, -0.56, ..., -0.12]
#
#   The first two vectors are CLOSE (similar meaning).
#   The third is FAR (different topic).
#
#   We measure closeness with COSINE SIMILARITY:
#   - 1.0 = identical meaning
#   - 0.0 = completely unrelated
#   - -1.0 = opposite meaning (rare in practice)
#
# WHY EMBEDDINGS (not keyword search):
#   Keyword search: "water consumption" won't find "hydration level"
#   Embedding search: both map to similar vectors → match!
#   This is called SEMANTIC SEARCH — search by meaning, not by words.
# ============================================================================

from app.modules.ai.llm.factory import get_llm_client
from app.shared.logging import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """
    Generates vector embeddings from text using the configured LLM provider.

    Uses the same LLM client factory — Ollama for local dev, OpenAI for production.
    The embedding model is different from the chat model:
    - Chat: llama3.1:8b (generates text)
    - Embedding: nomic-embed-text (generates vectors)

    Usage:
        generator = EmbeddingGenerator()
        vectors = await generator.embed_texts(["Hello world", "Goodbye world"])
        # vectors = [[0.12, 0.45, ...], [0.34, 0.67, ...]]
    """

    def __init__(self):
        self.client = get_llm_client()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Handles batching internally — some providers have limits
        on how many texts can be embedded in one API call.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (same order as input texts)
            Each vector has 768 dimensions (nomic-embed-text) or
            1536 dimensions (OpenAI text-embedding-3-small)
        """
        if not texts:
            return []

        # Process in batches of 32 (most APIs have batch limits)
        batch_size = 32
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self.client.embed(batch)
            all_embeddings.extend(embeddings)

        logger.info(
            "embeddings_generated",
            count=len(texts),
            dimensions=len(all_embeddings[0]) if all_embeddings else 0,
        )

        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate a single embedding for a search query.

        Convenience method — embeds one text and returns the vector.
        Used during retrieval (embed the user's question).
        """
        embeddings = await self.embed_texts([query])
        return embeddings[0] if embeddings else []
