# ============================================================================
# RAG — Retriever
# ============================================================================
# WHAT THIS FILE DOES:
#   Orchestrates the full retrieval pipeline:
#   1. Embed the user's question
#   2. Search pgvector for similar chunks
#   3. Build a formatted context string with source citations
#   4. Return context ready to inject into the LLM prompt
#
# THIS IS THE "R" IN RAG:
#   Retrieval-Augmented Generation
#   ├── Retrieval  ← THIS FILE (find relevant info from documents)
#   ├── Augmented  ← inject retrieved info into the prompt
#   └── Generation ← LLM generates answer using the context
#
# WHY A SEPARATE RETRIEVER (not just calling vector_store directly):
#   The retriever adds:
#   1. Query embedding (vector_store only does the search)
#   2. Context formatting (turn raw chunks into a readable prompt section)
#   3. Source citation building (for "Based on report.pdf, page 3...")
#   4. Token counting (ensure context fits in the LLM's context window)
#   5. Deduplication (same chunk might match multiple queries)
#
# RETRIEVAL QUALITY TIPS:
#   - More chunks = more context but more noise
#   - Higher threshold = fewer but more relevant results
#   - 5 chunks with 0.5 threshold is a good starting point
#   - If results are poor, try: rephrase query, lower threshold, adjust chunk size
# ============================================================================

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.rag.embeddings import EmbeddingGenerator
from app.modules.ai.rag.vector_store import VectorStore
from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedContext:
    """
    The result of a retrieval operation.

    formatted_context: Ready to inject into the LLM prompt
    sources: List of source references (for citation display in UI)
    chunk_count: How many chunks were retrieved
    total_tokens: Estimated tokens in the context (for context window management)
    """

    formatted_context: str
    sources: list[dict]       # [{filename, page_number, similarity}, ...]
    chunk_count: int
    total_tokens: int


class Retriever:
    """
    Full RAG retrieval pipeline.

    Usage:
        retriever = Retriever(session)
        context = await retriever.retrieve("How much iron do I need?", user_id)
        # context.formatted_context → "RELEVANT DOCUMENTS:\n[Source: report.pdf, p.3]..."
        # context.sources → [{"filename": "report.pdf", "page_number": 3, ...}]
    """

    def __init__(self, session: AsyncSession):
        self.vector_store = VectorStore(session)
        self.embedding_generator = EmbeddingGenerator()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        max_context_tokens: int = 2000,
    ) -> RetrievedContext:
        """
        Retrieve relevant document chunks for a query.

        PIPELINE:
        1. Embed the query text → vector
        2. Search pgvector for similar chunks
        3. Filter by token budget (don't exceed max_context_tokens)
        4. Format into a context string with citations
        5. Return context + source metadata

        Args:
            query: The user's question
            user_id: Only search this user's documents
            top_k: Maximum chunks to retrieve
            similarity_threshold: Minimum similarity (0-1)
            max_context_tokens: Token budget for the context

        Returns:
            RetrievedContext with formatted text and source info
        """
        # Step 1: Embed the query
        query_embedding = await self.embedding_generator.embed_query(query)

        if not query_embedding:
            logger.warning("empty_query_embedding", query=query[:50])
            return RetrievedContext(
                formatted_context="",
                sources=[],
                chunk_count=0,
                total_tokens=0,
            )

        # Step 2: Search for similar chunks
        results = await self.vector_store.similarity_search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if not results:
            logger.info("no_relevant_chunks", query=query[:50])
            return RetrievedContext(
                formatted_context="",
                sources=[],
                chunk_count=0,
                total_tokens=0,
            )

        # Step 3: Build context within token budget
        context_chunks = []
        sources = []
        total_tokens = 0

        for chunk in results:
            # Estimate tokens for this chunk (~4 chars per token)
            chunk_tokens = len(chunk["chunk_text"]) // 4

            # Stop if adding this chunk would exceed the budget
            if total_tokens + chunk_tokens > max_context_tokens:
                break

            context_chunks.append(chunk)
            total_tokens += chunk_tokens

            # Track sources (deduplicate by document + page)
            source = {
                "filename": chunk["filename"],
                "page_number": chunk["page_number"],
                "similarity": round(float(chunk["similarity"]), 3),
                "document_id": str(chunk["document_id"]),
            }
            if source not in sources:
                sources.append(source)

        # Step 4: Format context with citations
        formatted = self._format_context(context_chunks)

        logger.info(
            "retrieval_completed",
            query=query[:50],
            chunks_retrieved=len(context_chunks),
            total_tokens=total_tokens,
            sources=len(sources),
        )

        return RetrievedContext(
            formatted_context=formatted,
            sources=sources,
            chunk_count=len(context_chunks),
            total_tokens=total_tokens,
        )

    @staticmethod
    def _format_context(chunks: list[dict]) -> str:
        """
        Format retrieved chunks into a readable context for the LLM prompt.

        Each chunk gets a source citation header so the LLM can reference it.
        The LLM is instructed to cite sources in its response.

        Output format:
            RELEVANT INFORMATION FROM YOUR DOCUMENTS:

            [Source: blood_report.pdf, Page 3]
            The patient's iron level is 10.5 µg/dL...
            ---
            [Source: nutrition_guide.pdf, Page 12]
            Adults need 8-18mg of iron daily...
            ---
        """
        if not chunks:
            return ""

        parts = ["RELEVANT INFORMATION FROM YOUR DOCUMENTS:\n"]

        for chunk in chunks:
            page_info = f", Page {chunk['page_number']}" if chunk["page_number"] else ""
            header = f"[Source: {chunk['filename']}{page_info}]"
            parts.append(f"{header}\n{chunk['chunk_text']}\n---")

        parts.append(
            "\nUse the above information to help answer the user's question. "
            "Cite sources when referencing document content."
        )

        return "\n".join(parts)
