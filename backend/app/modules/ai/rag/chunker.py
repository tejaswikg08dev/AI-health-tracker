# ============================================================================
# RAG — Text Chunker
# ============================================================================
# WHAT THIS FILE DOES:
#   Splits document text into overlapping chunks for embedding.
#   This is step 2 of the RAG ingestion pipeline:
#     Upload → Extract → [CHUNK] → Embed → Store
#
# WHY CHUNKING:
#   1. LLMs have context limits (4K-128K tokens). A 50-page PDF won't fit.
#   2. Embeddings are more precise on smaller text (500 tokens vs 5000).
#   3. Retrieval is more accurate — we fetch just the relevant section,
#      not the entire document.
#
# CHUNK OVERLAP:
#   If we split at exactly 500 tokens, important info at the boundary is lost:
#     Chunk 1: "...the patient's iron level is"
#     Chunk 2: "10.5 µg/dL which is below normal..."
#   Neither chunk has the full sentence!
#
#   With 50-token overlap:
#     Chunk 1: "...the patient's iron level is 10.5 µg/dL which is"
#     Chunk 2: "iron level is 10.5 µg/dL which is below normal..."
#   Both chunks have the complete information.
#
# CHUNKING STRATEGY:
#   We use "recursive character text splitting" — the same approach used by
#   LangChain's RecursiveCharacterTextSplitter:
#   1. Try to split on paragraph boundaries (\n\n)
#   2. If paragraphs are too long, split on sentence boundaries (. ! ?)
#   3. If sentences are too long, split on word boundaries (spaces)
#   4. Last resort: split on character count
#
#   This preserves semantic boundaries — a chunk is a complete thought,
#   not a random 500-character slice.
# ============================================================================

from dataclasses import dataclass

from app.shared.logging import get_logger

logger = get_logger(__name__)

# Splitting separators in order of preference
# We try the first one; if chunks are still too big, try the next
SEPARATORS = [
    "\n\n",     # Paragraph boundary (best — preserves full paragraphs)
    "\n",       # Line boundary
    ". ",       # Sentence boundary
    "! ",       # Sentence boundary
    "? ",       # Sentence boundary
    "; ",       # Clause boundary
    ", ",       # Phrase boundary
    " ",        # Word boundary (last resort before raw split)
]


@dataclass
class TextChunk:
    """
    A single chunk of text from a document.

    text: The chunk content
    index: Position within the document (0-based)
    page_number: Which page this chunk is from (PDF) or None
    token_count: Estimated token count (for context window management)
    """

    text: str
    index: int
    page_number: int | None
    token_count: int


class TextChunker:
    """
    Splits document text into overlapping chunks.

    Args:
        chunk_size: Target chunk size in characters (~4 chars per token)
        chunk_overlap: Overlap between consecutive chunks in characters
        min_chunk_size: Minimum chunk size (skip tiny fragments)

    Usage:
        chunker = TextChunker(chunk_size=2000, chunk_overlap=200)
        chunks = chunker.chunk_text("Very long document text...", page_texts=[...])
    """

    def __init__(
        self,
        chunk_size: int = 2000,       # ~500 tokens (4 chars/token average)
        chunk_overlap: int = 200,     # ~50 tokens overlap
        min_chunk_size: int = 100,    # Skip chunks smaller than this
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        page_texts: list[str] | None = None,
    ) -> list[TextChunk]:
        """
        Split text into overlapping chunks.

        If page_texts is provided (from PDF), tracks which page each chunk
        came from. This enables source citations:
        "Based on your blood report [Source: report.pdf, Page 3]..."

        Returns:
            List of TextChunk objects, ordered by document position
        """
        if not text or not text.strip():
            return []

        # Build page boundaries for page tracking
        page_map = self._build_page_map(page_texts) if page_texts else None

        # Split the text recursively
        raw_chunks = self._recursive_split(text, SEPARATORS)

        # Create TextChunk objects with metadata
        chunks = []
        char_offset = 0

        for i, chunk_text in enumerate(raw_chunks):
            # Estimate token count (~4 characters per token for English)
            token_count = len(chunk_text) // 4

            # Find which page this chunk is from
            page_number = None
            if page_map:
                page_number = self._find_page(char_offset, page_map)

            chunks.append(TextChunk(
                text=chunk_text,
                index=i,
                page_number=page_number,
                token_count=token_count,
            ))

            # Track character offset (accounting for overlap)
            char_offset += len(chunk_text) - self.chunk_overlap

        logger.info(
            "text_chunked",
            total_chunks=len(chunks),
            avg_chunk_size=sum(len(c.text) for c in chunks) // max(len(chunks), 1),
        )

        return chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """
        Recursively split text using the best available separator.

        ALGORITHM:
        1. Try the first separator (e.g., paragraph boundary)
        2. Split the text on that separator
        3. Merge small adjacent pieces to reach chunk_size
        4. If any merged piece is still too big, recurse with next separator

        This ensures we always split at the best semantic boundary.
        """
        if len(text) <= self.chunk_size:
            return [text] if len(text) >= self.min_chunk_size else []

        # Try each separator
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                return self._merge_parts(parts, sep, separators)

        # No separator found — hard split by character count
        return self._hard_split(text)

    def _merge_parts(
        self,
        parts: list[str],
        separator: str,
        remaining_separators: list[str],
    ) -> list[str]:
        """
        Merge small parts into chunks of target size with overlap.

        After splitting on a separator, some pieces are tiny.
        We merge consecutive pieces until reaching chunk_size,
        then start a new chunk (with overlap from the previous one).
        """
        chunks = []
        current_chunk = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Would adding this part exceed chunk_size?
            test_chunk = current_chunk + separator + part if current_chunk else part

            if len(test_chunk) <= self.chunk_size:
                # Still fits — keep merging
                current_chunk = test_chunk
            else:
                # Exceeded — save current chunk
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk)

                # Start new chunk with overlap from the end of the previous one
                if current_chunk and self.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + separator + part
                else:
                    current_chunk = part

                # If this single part is too big, recurse with finer separator
                if len(current_chunk) > self.chunk_size:
                    sep_idx = SEPARATORS.index(separator) if separator in SEPARATORS else -1
                    next_seps = SEPARATORS[sep_idx + 1:] if sep_idx < len(SEPARATORS) - 1 else []
                    if next_seps:
                        sub_chunks = self._recursive_split(current_chunk, next_seps)
                        chunks.extend(sub_chunks)
                        current_chunk = ""
                    else:
                        # Last resort: hard split
                        chunks.extend(self._hard_split(current_chunk))
                        current_chunk = ""

        # Don't forget the last chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk)

        return chunks

    def _hard_split(self, text: str) -> list[str]:
        """Split text by character count when no separator works."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks

    def _build_page_map(self, page_texts: list[str]) -> list[tuple[int, int, int]]:
        """
        Build a map of (start_char, end_char, page_number) for page tracking.

        When joining page texts with \\n\\n, track where each page starts/ends
        so we can determine which page a chunk belongs to.
        """
        page_map = []
        offset = 0
        for i, page_text in enumerate(page_texts):
            start = offset
            end = offset + len(page_text)
            page_map.append((start, end, i + 1))  # Pages are 1-indexed
            offset = end + 2  # Account for \n\n separator
        return page_map

    @staticmethod
    def _find_page(char_offset: int, page_map: list[tuple[int, int, int]]) -> int | None:
        """Find which page a character offset falls in."""
        for start, end, page_num in page_map:
            if start <= char_offset < end:
                return page_num
        return page_map[-1][2] if page_map else None
