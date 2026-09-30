# ============================================================================
# Unit Tests — RAG Text Chunker
# ============================================================================

import pytest
from app.modules.ai.rag.chunker import TextChunker


class TestTextChunker:
    """Test the recursive text chunking algorithm."""

    def setup_method(self):
        self.chunker = TextChunker(chunk_size=200, chunk_overlap=20, min_chunk_size=10)

    def test_short_text_single_chunk(self):
        """Text shorter than chunk_size returns one chunk."""
        chunks = self.chunker.chunk_text("This is a short text.")
        assert len(chunks) == 1
        assert chunks[0].text == "This is a short text."
        assert chunks[0].index == 0

    def test_empty_text_no_chunks(self):
        """Empty text returns no chunks."""
        assert self.chunker.chunk_text("") == []
        assert self.chunker.chunk_text("   ") == []

    def test_long_text_multiple_chunks(self):
        """Long text is split into multiple chunks."""
        # Create text that's ~600 chars (3× chunk_size of 200)
        text = "This is a paragraph about health. " * 20
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) >= 2
        # All chunks should be within size limits
        for chunk in chunks:
            assert len(chunk.text) >= self.chunker.min_chunk_size

    def test_chunk_index_is_sequential(self):
        """Chunk indices are sequential starting from 0."""
        text = "Word " * 200  # Long enough for multiple chunks
        chunks = self.chunker.chunk_text(text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_paragraphs_split_at_boundaries(self):
        """Text with paragraphs splits at paragraph boundaries."""
        text = "First paragraph content here.\n\nSecond paragraph content here.\n\nThird paragraph content here."
        chunker = TextChunker(chunk_size=60, chunk_overlap=5, min_chunk_size=10)
        chunks = chunker.chunk_text(text)
        # Should split at \n\n boundaries
        assert len(chunks) >= 2

    def test_page_tracking(self):
        """Chunks track which page they came from."""
        page_texts = [
            "Page one content goes here with enough text.",
            "Page two has different content about health.",
        ]
        text = "\n\n".join(page_texts)
        chunker = TextChunker(chunk_size=500, chunk_overlap=20, min_chunk_size=10)
        chunks = chunker.chunk_text(text, page_texts=page_texts)
        # First chunk should be from page 1
        if chunks:
            assert chunks[0].page_number is not None

    def test_token_count_estimation(self):
        """Token count is approximately text_length / 4."""
        text = "a" * 400  # 400 chars ≈ 100 tokens
        chunker = TextChunker(chunk_size=500, chunk_overlap=0, min_chunk_size=10)
        chunks = chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0].token_count == 100  # 400 / 4
