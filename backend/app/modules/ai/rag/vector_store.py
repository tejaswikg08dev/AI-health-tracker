# ============================================================================
# RAG — Vector Store (pgvector)
# ============================================================================
# WHAT THIS FILE DOES:
#   Stores and searches document chunk embeddings using PostgreSQL + pgvector.
#   This is step 4 (store) and part of retrieval:
#     Upload → Extract → Chunk → Embed → [STORE IN PGVECTOR]
#     Query → Embed → [SEARCH PGVECTOR] → Return top matches
#
# WHY PGVECTOR (not Pinecone, ChromaDB, etc.):
#   1. Free — it's a PostgreSQL extension, no separate service
#   2. Same database — no extra infrastructure to manage
#   3. Transactional — chunks are stored in the same transaction as documents
#   4. Good enough — for < 1 million vectors, pgvector performs well
#   5. Production-ready — used by Supabase, Neon, and many startups
#
# HOW VECTOR SEARCH WORKS:
#   1. The user's question is embedded: "How much iron do I need?"
#      → [0.12, -0.45, 0.78, ..., 0.33]  (768 numbers)
#
#   2. pgvector calculates COSINE DISTANCE between the query vector
#      and every stored chunk vector.
#
#   3. Returns the TOP K chunks with the smallest distance
#      (smallest distance = most similar meaning).
#
#   4. The <=> operator is pgvector's cosine distance operator:
#      SELECT * FROM document_chunks
#      ORDER BY embedding <=> query_vector
#      LIMIT 5;
#
# INDEX TYPE (IVFFlat):
#   Without an index: linear scan — compare query with every vector.
#   With IVFFlat: approximate nearest neighbor — much faster.
#   IVFFlat divides vectors into clusters, only searches nearby clusters.
#   Tradeoff: ~95% recall (might miss 5% of exact matches) but 10-100x faster.
# ============================================================================

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    pgvector operations for document chunks.

    Handles: storing embeddings, similarity search, cleanup.
    Uses raw SQL with text() because pgvector operators (<=>) aren't
    natively supported by SQLAlchemy ORM.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def store_chunk(
        self,
        chunk_id: str,
        document_id: str,
        user_id: str,
        chunk_text: str,
        chunk_index: int,
        page_number: int | None,
        token_count: int,
        embedding: list[float],
    ) -> None:
        """
        Store a document chunk with its embedding vector.

        The embedding is stored as a pgvector 'vector' type column.
        PostgreSQL handles the binary storage and indexing.
        """
        # Convert Python list to pgvector format: '[0.1, 0.2, ...]'
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        await self.session.execute(
            text("""
                INSERT INTO document_chunks
                (id, document_id, user_id, chunk_text, chunk_index,
                 page_number, token_count, embedding, created_at)
                VALUES
                (:id, :document_id, :user_id, :chunk_text, :chunk_index,
                 :page_number, :token_count, :embedding::vector, NOW())
            """),
            {
                "id": chunk_id,
                "document_id": document_id,
                "user_id": user_id,
                "chunk_text": chunk_text,
                "chunk_index": chunk_index,
                "page_number": page_number,
                "token_count": token_count,
                "embedding": embedding_str,
            },
        )

    async def similarity_search(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float = 0.3,
    ) -> list[dict]:
        """
        Find the most similar document chunks to a query embedding.

        HOW IT WORKS:
        1. The query text has been embedded into a vector
        2. We calculate cosine distance between the query and all stored chunks
        3. Return the top K chunks with distance below the threshold

        COSINE DISTANCE vs COSINE SIMILARITY:
            pgvector's <=> operator returns DISTANCE (0 = identical, 2 = opposite)
            Similarity = 1 - distance
            We filter by: 1 - distance > threshold (only return relevant chunks)

        Args:
            user_id: Only search this user's documents
            query_embedding: The query's vector embedding
            top_k: Maximum chunks to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of dicts with: chunk_text, document filename, page_number, similarity
        """
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        result = await self.session.execute(
            text("""
                SELECT
                    dc.chunk_text,
                    dc.page_number,
                    dc.chunk_index,
                    d.filename,
                    d.id AS document_id,
                    -- Cosine similarity = 1 - cosine distance
                    1 - (dc.embedding <=> :query_embedding::vector) AS similarity
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.user_id = :user_id
                  AND d.status = 'processed'
                  -- Only return chunks above the similarity threshold
                  AND 1 - (dc.embedding <=> :query_embedding::vector) > :threshold
                ORDER BY dc.embedding <=> :query_embedding::vector  -- Closest first
                LIMIT :top_k
            """),
            {
                "user_id": user_id,
                "query_embedding": embedding_str,
                "threshold": similarity_threshold,
                "top_k": top_k,
            },
        )

        rows = result.mappings().all()

        logger.info(
            "vector_search_completed",
            user_id=user_id,
            results=len(rows),
            top_similarity=round(float(rows[0]["similarity"]), 3) if rows else 0,
        )

        return [dict(row) for row in rows]

    async def delete_by_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.

        Called when: user deletes an uploaded document.
        The chunks and their embeddings are removed.
        """
        result = await self.session.execute(
            text("""
                DELETE FROM document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id},
        )
        await self.session.flush()
        count = result.rowcount
        logger.info("chunks_deleted", document_id=document_id, count=count)
        return count

    async def get_chunk_count(self, user_id: str) -> int:
        """Count total chunks stored for a user."""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM document_chunks WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        return result.scalar_one()
