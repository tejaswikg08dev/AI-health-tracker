"""
Lambda 6: RAG Document Processor
Trigger: S3 PutObject event (user uploads PDF via FastAPI)
Flow: Download from S3 → Extract text → Chunk → Embed (Groq) → Store in pgvector
"""

import json
import uuid

import httpx

import sys
sys.path.insert(0, "..")
from shared.config import GROQ_API_KEY
from shared.db_utils import execute_update, get_db_connection
from shared.s3_utils import download_file


# Chunking config
CHUNK_SIZE = 2000       # ~500 tokens
CHUNK_OVERLAP = 200     # ~50 tokens overlap


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        # Parse key: documents/{user_id}/{document_id}/{filename}
        parts = key.split("/")
        if len(parts) < 4:
            print(f"Unexpected key format: {key}")
            continue

        user_id = parts[1]
        document_id = parts[2]
        filename = parts[3]

        print(f"Processing: {filename} (user={user_id}, doc={document_id})")

        try:
            # Step 1: Download file from S3
            file_content = download_file(key)

            # Step 2: Extract text
            if filename.lower().endswith(".pdf"):
                text = _extract_pdf_text(file_content)
            else:
                text = file_content.decode("utf-8", errors="replace")

            if not text.strip():
                _update_doc_status(document_id, "failed", "No text content extracted")
                continue

            # Step 3: Chunk the text
            chunks = _chunk_text(text)

            # Step 4: Generate embeddings (via Ollama or placeholder)
            embeddings = _generate_embeddings([c["text"] for c in chunks])

            # Step 5: Store chunks with embeddings in pgvector
            conn = get_db_connection()
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    cur.execute("""
                        INSERT INTO document_chunks
                        (id, document_id, user_id, chunk_text, chunk_index, page_number, token_count, embedding, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, NOW())
                    """, (
                        str(uuid.uuid4()), document_id, user_id,
                        chunk["text"], chunk["index"], chunk.get("page"),
                        len(chunk["text"]) // 4, embedding_str,
                    ))
                conn.commit()

            # Update document status
            _update_doc_status(document_id, "processed", None, len(chunks))

            print(f"✅ Processed {filename}: {len(chunks)} chunks")

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            _update_doc_status(document_id, "failed", str(e)[:500])

    return {"statusCode": 200}


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes."""
    import io
    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


def _chunk_text(text: str) -> list[dict]:
    """Simple chunking with overlap."""
    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk_text = text[start:end].strip()
        if len(chunk_text) >= 50:  # Skip tiny fragments
            chunks.append({"text": chunk_text, "index": index, "page": None})
            index += 1
        start = end - CHUNK_OVERLAP
    return chunks


def _generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings. Uses zero vectors as placeholder if no API available."""
    # In production, call Ollama, Groq, or OpenAI embedding API
    # For now, return placeholder vectors (768 dimensions)
    return [[0.0] * 768 for _ in texts]


def _update_doc_status(doc_id: str, status: str, error: str | None = None, chunk_count: int = 0):
    if error:
        execute_update("""
            UPDATE documents SET status = %(s)s, error_message = %(e)s WHERE id = %(id)s
        """, {"s": status, "e": error, "id": doc_id})
    else:
        execute_update("""
            UPDATE documents SET status = %(s)s, chunk_count = %(c)s WHERE id = %(id)s
        """, {"s": status, "c": chunk_count, "id": doc_id})
