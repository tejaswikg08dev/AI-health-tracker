# 🔍 Phase 4 Part 09a: RAG — Ingestion Pipeline

> **"Ingestion turns a 50-page PDF into searchable knowledge. Extract text, split into chunks, convert to vectors, store in pgvector. When the user asks a question later, we search these vectors to find the answer."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 09a (RAG Ingestion — Extract, Chunk, Embed) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.2 — Document-Based AI |
| **Previous** | [phase4-part09-ai-rag-overview.md](./phase4-part09-ai-rag-overview.md) |
| **Next** | [phase4-part09b-ai-rag-retrieval.md](./phase4-part09b-ai-rag-retrieval.md) |
| **Files in This Doc** | 3 files (document_processor.py, chunker.py, embeddings.py) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Hard (PDF extraction, recursive splitting algorithm, batch embedding) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: document_processor.py — Text Extraction](#processor)
3. [File 2: chunker.py — Recursive Text Splitting](#chunker)
4. [File 3: embeddings.py — Text to Vectors](#embeddings)
5. [The Ingestion Pipeline End-to-End](#pipeline)
6. [Design Decisions](#design-decisions)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Three files that form the ingestion pipeline — steps 1, 2, and 3 of turning a document into searchable knowledge:

```
Upload "Sleep Guide.pdf" (50 pages)
  │
  ▼ Step 1: EXTRACT
┌─── document_processor.py ───┐
│  PDF bytes → plain text      │
│  Track page boundaries       │
└──────────────┬──────────────┘
               │
               ▼ Step 2: CHUNK
┌─── chunker.py ──────────────┐
│  Long text → 100 chunks      │
│  ~500 tokens each            │
│  50-token overlap            │
│  Track page numbers          │
└──────────────┬──────────────┘
               │
               ▼ Step 3: EMBED
┌─── embeddings.py ───────────┐
│  Each chunk → 768-dim vector │
│  Batch processing (32/batch) │
│  Uses LLM provider's API     │
└──────────────┬──────────────┘
               │
               ▼ Step 4: STORE (Part 09b)
┌─── vector_store.py ─────────┐
│  Store in pgvector            │
└──────────────────────────────┘
```

---

<a name="processor"></a>
## 2. File 1: `document_processor.py` — Text Extraction

### Type This Code: `backend/app/modules/ai/rag/document_processor.py`

```python
# ============================================================================
# RAG — Document Processor
# ============================================================================
# WHAT THIS FILE DOES:
#   Extracts plain text from uploaded files (PDF, TXT, Markdown).
#   This is step 1 of the RAG ingestion pipeline:
#     Upload → [EXTRACT TEXT] → Chunk → Embed → Store
#
# WHY TEXT EXTRACTION:
#   LLMs work with text, not binary files.
#   A PDF is a complex binary format with fonts, images, and layout.
#   We need to extract just the readable text content.
#
# SUPPORTED FORMATS:
#   PDF → PyPDF2 extracts text page by page
#   TXT → read directly (already text)
#   MD  → read directly (Markdown is text)
#
# FUTURE: Could add DOCX (python-docx), HTML (BeautifulSoup), images (OCR)
# ============================================================================

from dataclasses import dataclass

from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessedDocument:
    """
    Result of document text extraction.

    text: The full extracted text content
    page_count: Number of pages (PDF) or None (text files)
    page_texts: Text per page (PDF) or [full_text] (text files)
    """

    text: str
    page_count: int | None
    page_texts: list[str]  # Text content per page


class DocumentProcessor:
    """
    Extracts text from uploaded documents.

    Usage:
        processor = DocumentProcessor()
        result = processor.process(file_bytes, "report.pdf", "pdf")
    """

    def process(
        self,
        file_content: bytes,
        filename: str,
        file_type: str,
    ) -> ProcessedDocument:
        """
        Extract text from a file based on its type.

        Args:
            file_content: Raw file bytes
            filename: Original filename (for logging)
            file_type: File extension without dot ("pdf", "txt", "md")

        Returns:
            ProcessedDocument with extracted text

        Raises:
            ValueError: if file type is not supported
        """
        file_type = file_type.lower().strip(".")

        if file_type == "pdf":
            return self._process_pdf(file_content, filename)
        elif file_type in ("txt", "md", "markdown", "text"):
            return self._process_text(file_content, filename)
        else:
            raise ValueError(
                f"Unsupported file type: '{file_type}'. "
                f"Supported: pdf, txt, md"
            )

    def _process_pdf(self, content: bytes, filename: str) -> ProcessedDocument:
        """
        Extract text from a PDF file using PyPDF2.

        We extract text PAGE BY PAGE so we can track which page
        each chunk came from (for source citations in RAG responses).
        """
        import io
        from PyPDF2 import PdfReader

        try:
            reader = PdfReader(io.BytesIO(content))
            page_texts = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    page_texts.append(text)

            full_text = "\n\n".join(page_texts)
            page_count = len(reader.pages)

            logger.info(
                "pdf_processed",
                filename=filename,
                pages=page_count,
                text_length=len(full_text),
            )

            return ProcessedDocument(
                text=full_text,
                page_count=page_count,
                page_texts=page_texts,
            )

        except Exception as e:
            logger.error("pdf_processing_error", filename=filename, error=str(e))
            raise ValueError(f"Failed to process PDF '{filename}': {str(e)}")

    def _process_text(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process a plain text or Markdown file."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        text = text.strip()

        logger.info("text_processed", filename=filename, text_length=len(text))

        return ProcessedDocument(
            text=text,
            page_count=None,
            page_texts=[text],
        )
```

### Key Concepts

**`io.BytesIO(content)` — In-Memory File**
- `PyPDF2.PdfReader` expects a file-like object, not raw bytes
- `io.BytesIO(content)` wraps bytes in a file-like interface — no temp file needed
- This is a common Python pattern: "make bytes act like a file"

**Page-by-Page Extraction**
- We track page boundaries because RAG citations reference specific pages
- "Based on your blood report [Source: report.pdf, Page 3]" — the page number comes from here

**Lazy Import (`import io; from PyPDF2 import PdfReader`)**
- `PyPDF2` is imported inside the method, not at the top of the file
- If the user only uploads text files, PyPDF2 is never loaded — saves startup time
- Also prevents import errors if PyPDF2 isn't installed (text files still work)

---

<a name="chunker"></a>
## 3. File 2: `chunker.py` — Recursive Text Splitting

### Type This Code: `backend/app/modules/ai/rag/chunker.py`

*(Full source code from the source file — type it character-for-character)*

```python
# ============================================================================
# RAG — Text Chunker
# ============================================================================
# CHUNKING STRATEGY:
#   We use "recursive character text splitting":
#   1. Try to split on paragraph boundaries (\n\n)
#   2. If paragraphs are too long, split on sentence boundaries (. ! ?)
#   3. If sentences are too long, split on word boundaries (spaces)
#   4. Last resort: split on character count
# ============================================================================

from dataclasses import dataclass
from app.shared.logging import get_logger

logger = get_logger(__name__)

SEPARATORS = [
    "\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ",
]


@dataclass
class TextChunk:
    text: str
    index: int
    page_number: int | None
    token_count: int


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 2000,       # ~500 tokens
        chunk_overlap: int = 200,     # ~50 tokens
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, page_texts: list[str] | None = None) -> list[TextChunk]:
        if not text or not text.strip():
            return []

        page_map = self._build_page_map(page_texts) if page_texts else None
        raw_chunks = self._recursive_split(text, SEPARATORS)

        chunks = []
        char_offset = 0
        for i, chunk_text in enumerate(raw_chunks):
            token_count = len(chunk_text) // 4
            page_number = self._find_page(char_offset, page_map) if page_map else None
            chunks.append(TextChunk(text=chunk_text, index=i, page_number=page_number, token_count=token_count))
            char_offset += len(chunk_text) - self.chunk_overlap

        logger.info("text_chunked", total_chunks=len(chunks),
                    avg_chunk_size=sum(len(c.text) for c in chunks) // max(len(chunks), 1))
        return chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if len(text) >= self.min_chunk_size else []
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                return self._merge_parts(parts, sep, separators)
        return self._hard_split(text)

    def _merge_parts(self, parts, separator, remaining_separators):
        chunks = []
        current_chunk = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            test_chunk = current_chunk + separator + part if current_chunk else part
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk)
                if current_chunk and self.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + separator + part
                else:
                    current_chunk = part
                if len(current_chunk) > self.chunk_size:
                    sep_idx = SEPARATORS.index(separator) if separator in SEPARATORS else -1
                    next_seps = SEPARATORS[sep_idx + 1:] if sep_idx < len(SEPARATORS) - 1 else []
                    if next_seps:
                        sub_chunks = self._recursive_split(current_chunk, next_seps)
                        chunks.extend(sub_chunks)
                        current_chunk = ""
                    else:
                        chunks.extend(self._hard_split(current_chunk))
                        current_chunk = ""
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk)
        return chunks

    def _hard_split(self, text):
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks

    def _build_page_map(self, page_texts):
        page_map = []
        offset = 0
        for i, page_text in enumerate(page_texts):
            start = offset
            end = offset + len(page_text)
            page_map.append((start, end, i + 1))
            offset = end + 2
        return page_map

    @staticmethod
    def _find_page(char_offset, page_map):
        for start, end, page_num in page_map:
            if start <= char_offset < end:
                return page_num
        return page_map[-1][2] if page_map else None
```

### The Recursive Splitting Algorithm Explained

```
INPUT: "Chapter 1: Sleep.\n\nMagnesium helps sleep. Almonds are rich in it.\n\nChapter 2: Exercise.\n\n..."
CHUNK_SIZE: 2000 chars, OVERLAP: 200 chars

STEP 1: Try splitting on "\n\n" (paragraphs)
  → ["Chapter 1: Sleep.", "Magnesium helps sleep. Almonds are rich in it.", "Chapter 2: Exercise.", ...]
  → Each paragraph fits in 2000 chars ✅

STEP 2: Merge small paragraphs up to chunk_size
  → "Chapter 1: Sleep.\n\nMagnesium helps sleep. Almonds are rich in it." (merged — still under 2000)

STEP 3: If any merged chunk > 2000, recurse with "\n" (lines)
  → Then "." (sentences) → Then " " (words) → Then hard split

STEP 4: Add overlap between chunks
  → Chunk 1 ends with "...rich in magnesium and"
  → Chunk 2 starts with "magnesium and zinc help..." (overlapping 200 chars)
```

### Why This Algorithm (Not Just Split Every 500 Chars)

| Approach | Problem |
|----------|---------|
| Fixed 500-char split | Cuts mid-sentence: "The patient's iron level is\|10.5 µg/dL" |
| Split on sentences only | Huge variation: 1 sentence = 10 chars, another = 5000 chars |
| Split on paragraphs only | A single paragraph might be 10,000 chars (too big) |
| **Recursive** (ours) | Always splits at the best boundary. Paragraphs first, then sentences, then words. Consistent chunk sizes with semantic coherence. |

---

<a name="embeddings"></a>
## 4. File 3: `embeddings.py` — Text to Vectors

### Type This Code: `backend/app/modules/ai/rag/embeddings.py`

```python
# ============================================================================
# RAG — Embedding Generator
# ============================================================================
# WHAT THIS FILE DOES:
#   Converts text into vector embeddings (arrays of numbers).
#   Uses the same LLM provider factory — Ollama for dev, OpenAI for prod.
# ============================================================================

from app.modules.ai.llm.factory import get_llm_client
from app.shared.logging import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """
    Generates vector embeddings from text using the configured LLM provider.

    The embedding model is different from the chat model:
    - Chat: llama3.1:8b (generates text)
    - Embedding: nomic-embed-text (generates vectors)
    """

    def __init__(self):
        self.client = get_llm_client()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        Processes in batches of 32 (most APIs have batch limits).
        """
        if not texts:
            return []

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
        Convenience method for retrieval.
        """
        embeddings = await self.embed_texts([query])
        return embeddings[0] if embeddings else []
```

### Key Concepts

**Reuses the LLM Factory**
```python
self.client = get_llm_client()
```
- Same factory from Part 08b — returns Ollama, Groq, or OpenAI based on config
- Calls `client.embed(texts)` — the abstract method from `BaseLLMClient`
- Ollama uses `nomic-embed-text` (768 dims), OpenAI uses `text-embedding-3-small` (1536 dims)

**Batch Processing**
```python
for i in range(0, len(texts), batch_size):
    batch = texts[i : i + batch_size]
    embeddings = await self.client.embed(batch)
```
- A 50-page document might produce 100 chunks — can't embed all at once
- Batch size 32 is a common limit (OpenAI allows up to 2048, Ollama varies)
- `range(0, len(texts), 32)` → process in groups: [0:32], [32:64], [64:96], [96:100]

**Two Methods for Two Use Cases**
- `embed_texts(texts)` — bulk embedding during document ingestion (100 chunks at once)
- `embed_query(query)` — single embedding during retrieval (the user's question)

---

<a name="pipeline"></a>
## 5. The Ingestion Pipeline End-to-End

```
User uploads "Sleep Guide.pdf" via POST /ai/documents
  │
  ▼
AI Service receives the file
  │
  ▼
DocumentProcessor.process(file_bytes, "Sleep Guide.pdf", "pdf")
  → PyPDF2 extracts text page by page
  → ProcessedDocument(text="Chapter 1...", page_count=50, page_texts=[...])
  │
  ▼
TextChunker(chunk_size=2000, chunk_overlap=200).chunk_text(text, page_texts)
  → Recursive split: paragraphs → sentences → words
  → 100 TextChunk objects, each ~500 tokens
  → Each chunk knows its page_number (for citations)
  │
  ▼
EmbeddingGenerator().embed_texts([chunk.text for chunk in chunks])
  → Batch of 32 texts → LLM embed API → 768-dim vectors
  → 100 embedding vectors (one per chunk)
  │
  ▼
VectorStore.store_chunk(...) × 100  (Part 09b)
  → INSERT INTO document_chunks (text, embedding, page_number, ...)
  → pgvector stores each embedding as a vector column
  │
  ▼
Done! Document is now searchable.
Next question mentioning "magnesium" or "sleep foods" will find the right chunks.
```

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision: Chunk Size 2000 Chars (~500 Tokens)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Chunk Size                                        │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: 2000 characters (~500 tokens) with 200-char overlap        │
│                                                                     │
│  WHY 500 TOKENS:                                                    │
│  • Precise embeddings — smaller chunks = more focused vectors       │
│  • Fits context window — 5 chunks × 500 tokens = 2500 tokens       │
│    (leaves room for system prompt + user message + response)        │
│  • Matches LangChain defaults — industry-validated parameter        │
│                                                                     │
│  WHY NOT SMALLER (100 tokens):                                      │
│  • Too fragmented — single sentences lose context                   │
│  • More chunks = more storage + slower search                       │
│                                                                     │
│  WHY NOT LARGER (2000 tokens):                                      │
│  • Imprecise embeddings — "this chunk is about nutrition" (vague)   │
│  • Fewer chunks fit in context window                               │
│  • Wastes tokens on irrelevant surrounding text                     │
│                                                                     │
│  WHY 200-CHAR OVERLAP (~50 tokens):                                 │
│  • Prevents losing context at boundaries                            │
│  • 10% overlap is the industry standard                             │
│  • Too much overlap = duplicate content, wasted storage             │
│                                                                     │
│  INTERVIEW TIP: "We use 500-token chunks with 50-token overlap.     │
│  500 tokens is the sweet spot: precise enough for accurate          │
│  embeddings, large enough for semantic coherence. Overlap prevents  │
│  information loss at chunk boundaries."                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`io.BytesIO`** | Wrap bytes in a file-like interface | PDF processing |
| 2 | **`PdfReader`** | PyPDF2 class for reading PDF pages | `_process_pdf` |
| 3 | **Page tracking** | Extract per-page text for source citations | `ProcessedDocument.page_texts` |
| 4 | **Recursive text splitting** | Split on best boundary: paragraph → sentence → word | `_recursive_split` |
| 5 | **SEPARATORS priority** | `\n\n` (best) → `. ` → ` ` → hard split (worst) | Module-level constant |
| 6 | **Chunk overlap** | Shared text at boundaries prevents info loss | `_merge_parts` overlap logic |
| 7 | **`TextChunk` dataclass** | Chunk text + index + page_number + token_count | Chunker output |
| 8 | **Token estimation** | `len(text) // 4` — ~4 characters per English token | `chunk_text` |
| 9 | **Batch embedding** | Process 32 texts at a time (API batch limits) | `embed_texts` |
| 10 | **`embed_query` convenience** | Single text → single vector (for retrieval) | Search queries |
| 11 | **Lazy imports** | Import PyPDF2 inside method (not at top) | `_process_pdf` |
| 12 | **Page map** | `(start_char, end_char, page_number)` tuples | `_build_page_map` |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: How does your document chunking work?
**A:** "We use recursive character text splitting — the same approach as LangChain's RecursiveCharacterTextSplitter. We try to split on paragraph boundaries first (`\\n\\n`). If a paragraph exceeds 2000 characters, we split on sentence boundaries (`. `). If a sentence is still too long, we split on word boundaries (spaces). Last resort: hard split by character count. Each level preserves more semantic coherence. We add 200-character overlap between chunks to prevent losing context at boundaries."

### Q2: Why 500 tokens per chunk?
**A:** "Sweet spot between precision and coherence. Smaller chunks (100 tokens) are too fragmented — a single sentence like 'Take 400mg magnesium daily' loses the context of WHY. Larger chunks (2000 tokens) produce vague embeddings — 'this chunk is about nutrition' instead of 'this chunk is about magnesium and sleep.' 500 tokens typically captures a complete paragraph or concept. With 5 retrieved chunks, we use ~2500 tokens of context — leaving room for the system prompt, user question, and response."

### Q3: How do you track which page a chunk came from?
**A:** "During PDF processing, we extract text page by page and build a page map — a list of `(start_char, end_char, page_number)` tuples. When creating chunks, we track the character offset in the original text and look up which page that offset falls in. This enables citations: 'Based on your report [Source: report.pdf, Page 3].' Text files don't have pages, so `page_number` is None."

### Q4: How does the embedding generator reuse the LLM factory?
**A:** "The EmbeddingGenerator calls `get_llm_client()` — the same cached factory from Part 08b. The returned client (Ollama, Groq, or OpenAI) implements `embed()` from the BaseLLMClient interface. Ollama uses the nomic-embed-text model (768 dimensions), OpenAI uses text-embedding-3-small (1536 dimensions). The generator handles batching (32 texts per API call) and provides a convenience method for single queries."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 09: RAG Pipeline Overview](./phase4-part09-ai-rag-overview.md) |
| ➡️ Next | [Phase 4 Part 09b: RAG Retrieval](./phase4-part09b-ai-rag-retrieval.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### RAG Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **09a** | ✅ **You are here** | RAG Ingestion (Extract, Chunk, Embed) |
| 09b | ⬜ Next | RAG Retrieval (Vector Search, Context Format) |
| 09c | ⬜ | RAG Connections & Flows |

---

**End of Phase 4 Part 09a: RAG Ingestion Pipeline**

*Documents are now extractable, chunkable, and embeddable. Next: the retrieval side — searching pgvector and formatting context for the LLM.*
