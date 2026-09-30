# ============================================================================
# AI Module — Router (API Endpoints)
# ============================================================================
# ENDPOINTS:
#   POST /api/v1/ai/chat              → Chat with AI (agent or direct mode)
#   GET  /api/v1/ai/chat/stream       → SSE streaming chat
#   GET  /api/v1/ai/chat/history      → Get past conversations
#   POST /api/v1/ai/documents         → Upload a document for RAG
#   GET  /api/v1/ai/documents         → List uploaded documents
#   DELETE /api/v1/ai/documents/:id   → Delete a document
#   POST /api/v1/ai/insights          → Generate on-demand insight
#   GET  /api/v1/ai/insights          → List past insights
#   POST /api/v1/ai/weekly-report     → Generate weekly report
# ============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import StreamingResponse

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.ai.schemas import (
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    DocumentListResponse,
    DocumentResponse,
    InsightListResponse,
    InsightResponse,
)
from app.modules.ai.service import AiService
from app.modules.auth.router import get_current_user_id
from app.modules.auth.service import AuthService
from app.redis_client import get_redis_client
from app.shared.base_schemas import SuccessResponse

router = APIRouter()


# ── Dependencies ──

async def get_ai_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> AiService:
    return AiService(session, redis_client)


async def get_user_name(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> tuple[UUID, str]:
    """Get user ID and name for AI context."""
    auth_service = AuthService(session, redis_client)
    user = await auth_service.get_current_user(user_id)
    return user_id, user.full_name


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================


@router.post(
    "/chat",
    summary="Chat with AI health coach",
)
async def chat(
    data: ChatRequest,
    user_info: tuple[UUID, str] = Depends(get_user_name),
    service: AiService = Depends(get_ai_service),
) -> dict:
    """
    Chat with the AI health coach.

    Two modes:
    - use_agent=true (default): Agent mode with tool calling. Slower but can fetch
      real data, check streaks, search documents, find correlations.
    - use_agent=false: Direct LLM chat. Faster but only uses conversation context.

    Returns the AI's response as a JSON object.
    For streaming (word-by-word), use the /chat/stream endpoint instead.
    """
    user_id, user_name = user_info
    response = await service.chat(user_id, user_name, data.message, data.use_agent)
    return {"response": response}


@router.get(
    "/chat/stream",
    summary="Stream AI chat response (SSE)",
)
async def stream_chat(
    message: str,
    user_info: tuple[UUID, str] = Depends(get_user_name),
    service: AiService = Depends(get_ai_service),
) -> StreamingResponse:
    """
    Stream the AI response word-by-word using Server-Sent Events (SSE).

    This powers the ChatGPT-like typing effect in the UI.
    The response appears incrementally as the AI generates it.

    Uses direct mode only (no agent tools during streaming).

    Frontend usage (JavaScript):
        const eventSource = new EventSource("/api/v1/ai/chat/stream?message=...");
        eventSource.onmessage = (e) => { appendToChat(e.data); };
    """
    user_id, user_name = user_info

    async def event_generator():
        async for chunk in service.stream_chat(user_id, user_name, message):
            # SSE format: "data: <content>\n\n"
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Tell Nginx not to buffer SSE
        },
    )


@router.get(
    "/chat/history",
    response_model=ChatHistoryResponse,
    summary="Get chat history",
)
async def get_chat_history(
    user_id: UUID = Depends(get_current_user_id),
    service: AiService = Depends(get_ai_service),
) -> ChatHistoryResponse:
    """Get the user's recent chat messages."""
    messages = await service.get_chat_history(user_id, limit=50)
    return ChatHistoryResponse(
        messages=[ChatMessage.model_validate(m) for m in messages]
    )


# ============================================================================
# DOCUMENT ENDPOINTS (RAG)
# ============================================================================


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document for RAG",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF, TXT, or MD file"),
    user_id: UUID = Depends(get_current_user_id),
    service: AiService = Depends(get_ai_service),
) -> DocumentResponse:
    """
    Upload a health document (PDF, TXT, Markdown) for RAG.

    The document is processed in the background:
    1. Text extracted from file
    2. Split into chunks (~500 tokens each)
    3. Each chunk embedded (text → vector)
    4. Stored in pgvector for semantic search

    After processing (status="processed"), the AI can reference this
    document when answering questions.
    """
    # Validate file type
    filename = file.filename or "unknown"
    file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if file_type not in ("pdf", "txt", "md", "markdown", "text"):
        return DocumentResponse(
            id="00000000-0000-0000-0000-000000000000",
            filename=filename,
            file_type=file_type,
            file_size=0,
            page_count=None,
            status="failed",
            chunk_count=0,
            created_at=None,
        )

    content = await file.read()
    file_size = len(content)

    doc = await service.upload_document(
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        file_content=content,
        file_size=file_size,
    )

    return DocumentResponse.model_validate(doc)


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
)
async def list_documents(
    user_id: UUID = Depends(get_current_user_id),
    service: AiService = Depends(get_ai_service),
) -> DocumentListResponse:
    """Get all documents uploaded by the current user."""
    docs = await service.get_documents(user_id)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs]
    )


@router.delete(
    "/documents/{document_id}",
    response_model=SuccessResponse,
    summary="Delete a document",
)
async def delete_document(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: AiService = Depends(get_ai_service),
) -> SuccessResponse:
    """Delete a document and all its chunks/embeddings."""
    deleted = await service.delete_document(user_id, document_id)
    if not deleted:
        return SuccessResponse(message="Document not found")
    return SuccessResponse(message="Document deleted successfully")


# ============================================================================
# INSIGHT ENDPOINTS
# ============================================================================


@router.post(
    "/insights",
    response_model=InsightResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI insight",
)
async def generate_insight(
    user_id: UUID = Depends(get_current_user_id),
    service: AiService = Depends(get_ai_service),
) -> InsightResponse:
    """Generate an on-demand AI insight based on current habit data."""
    insight = await service.generate_insight(user_id)
    return InsightResponse.model_validate(insight)


@router.get(
    "/insights",
    response_model=InsightListResponse,
    summary="List AI insights",
)
async def list_insights(
    user_id: UUID = Depends(get_current_user_id),
    service: AiService = Depends(get_ai_service),
) -> InsightListResponse:
    """Get recent AI-generated insights."""
    insights = await service.get_insights(user_id)
    return InsightListResponse(
        insights=[InsightResponse.model_validate(i) for i in insights]
    )


@router.post(
    "/weekly-report",
    response_model=InsightResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate weekly report",
)
async def generate_weekly_report(
    user_info: tuple[UUID, str] = Depends(get_user_name),
    service: AiService = Depends(get_ai_service),
) -> InsightResponse:
    """
    Generate a comprehensive weekly health report using the agentic workflow.

    Pipeline: DataCollector → Analyzer → ReportWriter
    Takes 10-30 seconds depending on the LLM provider.
    """
    user_id, user_name = user_info
    insight = await service.generate_weekly_report(user_id, user_name)
    return InsightResponse.model_validate(insight)
