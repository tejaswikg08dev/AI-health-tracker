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
        # result.text = "Patient: Shreya..."
        # result.page_count = 5
        # result.page_texts = ["Page 1 text...", "Page 2 text...", ...]
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

        HOW PDF TEXT EXTRACTION WORKS:
            PDFs store text as positioned characters, not paragraphs.
            PyPDF2 reconstructs text by reading character positions.
            It's not perfect — tables and multi-column layouts may be messy.
            For production, you'd use 'unstructured' library or AWS Textract.

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
                # Clean up common PDF extraction artifacts
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
        """
        Process a plain text or Markdown file.

        Much simpler than PDF — just decode bytes to string.
        We try UTF-8 first, fall back to latin-1 (handles most files).
        """
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        text = text.strip()

        logger.info(
            "text_processed",
            filename=filename,
            text_length=len(text),
        )

        return ProcessedDocument(
            text=text,
            page_count=None,       # Text files don't have pages
            page_texts=[text],     # Entire content as one "page"
        )
