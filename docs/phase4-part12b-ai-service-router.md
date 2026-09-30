# 🤖 Phase 4 Part 12b: AI — Service & Router

> **"The AI service is the largest service in the project — 7 public methods orchestrating LLM, RAG, agents, and workflows. The router is the most feature-rich — 9 endpoints including SSE streaming and file upload. Together, they turn 39 AI files into a production API."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 12b (AI Service + Router — Full Source) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.5 — AI Endpoints & SSE Streaming |
| **Previous** | [phase4-part12a-ai-models-schemas.md](./phase4-part12a-ai-models-schemas.md) |
| **Next** | [phase4-part12c-ai-migration.md](./phase4-part12c-ai-migration.md) |
| **Files in This Doc** | 2 files (service.py ~280 lines, router.py ~220 lines) |
| **Time to Type** | ~75 minutes |
| **Difficulty** | ★★ Hard (cross-layer orchestration, SSE streaming, file upload, token tracking) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: service.py — The AI Orchestrator](#service)
3. [Service Method-by-Method Walkthrough](#service-walkthrough)
4. [File 2: router.py — 9 Endpoints + SSE](#router)
5. [Router Key Endpoints Explained](#router-walkthrough)
6. [How Service and Router Connect](#connections)
7. [How to Verify Your Work](#verify)
8. [What You Learned](#what-you-learned)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

| File | Methods | What It Does |
|------|---------|-------------|
| `service.py` | 7 public + 4 private | Orchestrates ALL AI: chat, RAG upload, insights, weekly report |
| `router.py` | 9 endpoints | HTTP layer: POST chat, GET stream (SSE), POST upload, etc. |

### Service Method Map

| # | Method | AI Layers Used | LLM Calls |
|---|--------|---------------|-----------|
| 1 | `chat()` | Agent OR direct LLM | 2-5 (agent) or 1 (direct) |
| 2 | `stream_chat()` | Direct LLM only (streaming) | 1 (streamed) |
| 3 | `get_chat_history()` | Database only | 0 |
| 4 | `upload_document()` | RAG pipeline (all 4 steps) | 0 LLM chat, N embed calls |
| 5 | `get_documents()` | Database only | 0 |
| 6 | `delete_document()` | Database (chunks + doc) | 0 |
| 7 | `generate_insight()` | DataCollector + LLM | 1 |
| 8 | `get_insights()` | Database only | 0 |
| 9 | `generate_weekly_report()` | Full workflow (3 steps) | 2 (analyze + write) |

---

<a name="service"></a>
## 2. File 1: `service.py` — The AI Orchestrator

### Type This Code: `backend/app/modules/ai/service.py`

*(Full source code — type character for character from the actual source file. This is ~280 lines.)*

```python
# ============================================================================
# AI Module — Service Layer
# ============================================================================
# WHAT THIS FILE DOES:
#   Orchestrates ALL AI features: chat (direct + agent), document upload/RAG,
#   insight generation, and weekly report workflow.
#   This is the single entry point the router calls.
#
# FEATURES:
#   1. Chat (direct LLM)  — fast, simple Q&A without tool calling
#   2. Chat (agent mode)  — ReAct agent with tools, data fetching, reasoning
#   3. Streaming chat      — SSE word-by-word response for the chat UI
#   4. Document upload     — process PDF/text for RAG
#   5. Document delete     — remove document and its chunks/embeddings
#   6. Generate insight    — on-demand AI analysis of current data
#   7. Weekly report       — run the full agentic workflow pipeline
# ============================================================================

import uuid
from typing import AsyncGenerator
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.agents.health_coach import HealthCoachAgent
from app.modules.ai.llm.base_client import LLMMessage
from app.modules.ai.llm.factory import get_llm_client
from app.modules.ai.llm.prompt_templates import HEALTH_COACH_SYSTEM, INSIGHT_PROMPT
from app.modules.ai.llm.token_tracker import TokenTracker
from app.modules.ai.models import AiChatMessage, AiInsight, Document, DocumentChunk
from app.modules.ai.rag.chunker import TextChunker
from app.modules.ai.rag.document_processor import DocumentProcessor
from app.modules.ai.rag.embeddings import EmbeddingGenerator
from app.modules.ai.rag.vector_store import VectorStore
from app.modules.ai.workflows.weekly_report.analyzer import Analyzer
from app.modules.ai.workflows.weekly_report.data_collector import DataCollector
from app.modules.ai.workflows.weekly_report.report_writer import ReportWriter
from app.modules.habits.repository import HabitRepository
from app.shared.date_utils import today_utc
from app.shared.logging import get_logger

logger = get_logger(__name__)


class AiService:
    """
    AI service — orchestrates chat, RAG, agents, and workflows.
    All AI features go through this service.
    """

    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.session = session
        self.redis = redis_client
        self.llm = get_llm_client()
        self.token_tracker = TokenTracker(redis_client)

    # ══════════════════════════════════════════════════════════════════
    # CHAT
    # ══════════════════════════════════════════════════════════════════

    async def chat(
        self, user_id: UUID, user_name: str, message: str, use_agent: bool = True,
    ) -> str:
        """Chat with the AI — agent mode (tools) or direct mode (fast)."""
        allowed, remaining = await self.token_tracker.check_limit(str(user_id))
        if not allowed:
            return "You've reached your daily AI usage limit. Try again tomorrow!"

        await self._save_chat_message(user_id, "user", message, 0)

        if use_agent:
            response = await self._agent_chat(user_id, user_name, message)
        else:
            response = await self._direct_chat(user_id, user_name, message)

        await self._save_chat_message(user_id, "assistant", response, 0)
        await self.session.commit()
        return response

    async def stream_chat(
        self, user_id: UUID, user_name: str, message: str,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response word by word using SSE."""
        await self._save_chat_message(user_id, "user", message, 0)

        habits_repo = HabitRepository(self.session)
        habits = await habits_repo.get_user_habits(user_id)
        system = HEALTH_COACH_SYSTEM.render(
            user_name=user_name, timezone="UTC", habit_count=len(habits),
        )

        history = await self._get_recent_messages(user_id, limit=10)
        messages = [LLMMessage(role="system", content=system)]
        for msg in history:
            messages.append(LLMMessage(role=msg.role, content=msg.content))
        messages.append(LLMMessage(role="user", content=message))

        full_response = ""
        async for chunk in self.llm.stream_chat(messages):
            full_response += chunk
            yield chunk

        await self._save_chat_message(user_id, "assistant", full_response, 0)
        await self.session.commit()

    async def get_chat_history(self, user_id: UUID, limit: int = 50) -> list[AiChatMessage]:
        return await self._get_recent_messages(user_id, limit)

    # ══════════════════════════════════════════════════════════════════
    # DOCUMENTS (RAG)
    # ══════════════════════════════════════════════════════════════════

    async def upload_document(
        self, user_id: UUID, filename: str, file_type: str,
        file_content: bytes, file_size: int,
    ) -> Document:
        """Upload and process a document for RAG."""
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id, user_id=user_id, filename=filename,
            file_type=file_type, file_size=file_size, status="processing",
        )
        self.session.add(doc)
        await self.session.flush()

        try:
            processor = DocumentProcessor()
            processed = processor.process(file_content, filename, file_type)
            doc.page_count = processed.page_count

            chunker = TextChunker(chunk_size=2000, chunk_overlap=200)
            chunks = chunker.chunk_text(processed.text, processed.page_texts)

            if not chunks:
                doc.status = "failed"
                doc.error_message = "No text content could be extracted"
                await self.session.commit()
                return doc

            embedder = EmbeddingGenerator()
            embeddings = await embedder.embed_texts([c.text for c in chunks])

            vector_store = VectorStore(self.session)
            for chunk, embedding in zip(chunks, embeddings):
                await vector_store.store_chunk(
                    chunk_id=str(uuid.uuid4()), document_id=str(doc_id),
                    user_id=str(user_id), chunk_text=chunk.text,
                    chunk_index=chunk.index, page_number=chunk.page_number,
                    token_count=chunk.token_count, embedding=embedding,
                )

            doc.status = "processed"
            doc.chunk_count = len(chunks)
            await self.session.commit()

            logger.info("document_processed", doc_id=str(doc_id),
                       filename=filename, chunks=len(chunks))

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)[:500]
            await self.session.commit()
            logger.error("document_processing_error", filename=filename, error=str(e))

        return doc

    async def get_documents(self, user_id: UUID) -> list[Document]:
        result = await self.session.execute(
            select(Document).where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, user_id: UUID, document_id: UUID) -> bool:
        await self.session.execute(
            sa_delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        result = await self.session.execute(
            sa_delete(Document).where(
                Document.id == document_id, Document.user_id == user_id,
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    # ══════════════════════════════════════════════════════════════════
    # INSIGHTS + WEEKLY REPORT
    # ══════════════════════════════════════════════════════════════════

    async def generate_insight(self, user_id: UUID) -> AiInsight:
        collector = DataCollector(self.session, user_id)
        data_summary = await collector.collect()

        prompt = INSIGHT_PROMPT.render(data_context=data_summary)
        response = await self.llm.chat(
            messages=[
                LLMMessage(role="system", content="Generate a brief, actionable health insight."),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.5, max_tokens=300,
        )

        insight = AiInsight(
            user_id=user_id, insight_type="on_demand",
            title="Health Insight", content=response.content,
            tokens_used=response.total_tokens,
        )
        self.session.add(insight)
        await self.session.commit()
        await self.session.refresh(insight)
        await self.token_tracker.track_usage(
            str(user_id), response.input_tokens, response.output_tokens
        )
        return insight

    async def get_insights(self, user_id: UUID, limit: int = 10) -> list[AiInsight]:
        result = await self.session.execute(
            select(AiInsight).where(AiInsight.user_id == user_id)
            .order_by(AiInsight.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def generate_weekly_report(self, user_id: UUID, user_name: str) -> AiInsight:
        collector = DataCollector(self.session, user_id)
        data_summary = await collector.collect()

        analyzer = Analyzer(self.llm)
        analysis, analysis_tokens = await analyzer.analyze(data_summary)

        writer = ReportWriter(self.llm, user_name)
        report, report_tokens = await writer.write(data_summary, analysis)

        total_tokens = analysis_tokens + report_tokens
        insight = AiInsight(
            user_id=user_id, insight_type="weekly_report",
            title=f"Weekly Report — {today_utc()}", content=report,
            tokens_used=total_tokens,
        )
        self.session.add(insight)
        await self.session.commit()
        await self.session.refresh(insight)
        await self.token_tracker.track_usage(str(user_id), total_tokens // 2, total_tokens // 2)

        logger.info("weekly_report_generated", user_id=str(user_id), tokens=total_tokens)
        return insight

    # ══════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════

    async def _agent_chat(self, user_id: UUID, user_name: str, message: str) -> str:
        agent = await HealthCoachAgent.create(
            session=self.session, redis_client=self.redis,
            user_id=user_id, user_name=user_name,
        )
        response = await agent.chat(message)
        await self.token_tracker.track_usage(
            str(user_id), agent.total_tokens // 2, agent.total_tokens // 2
        )
        return response

    async def _direct_chat(self, user_id: UUID, user_name: str, message: str) -> str:
        habits_repo = HabitRepository(self.session)
        habits = await habits_repo.get_user_habits(user_id)
        system = HEALTH_COACH_SYSTEM.render(
            user_name=user_name, timezone="UTC", habit_count=len(habits),
        )
        history = await self._get_recent_messages(user_id, limit=10)
        messages = [LLMMessage(role="system", content=system)]
        for msg in history:
            messages.append(LLMMessage(role=msg.role, content=msg.content))
        messages.append(LLMMessage(role="user", content=message))

        response = await self.llm.chat(messages=messages, temperature=0.7, max_tokens=1024)
        await self.token_tracker.track_usage(
            str(user_id), response.input_tokens, response.output_tokens
        )
        return response.content

    async def _save_chat_message(self, user_id: UUID, role: str, content: str, tokens: int) -> None:
        msg = AiChatMessage(user_id=user_id, role=role, content=content, tokens_used=tokens)
        self.session.add(msg)
        await self.session.flush()

    async def _get_recent_messages(self, user_id: UUID, limit: int = 10) -> list[AiChatMessage]:
        result = await self.session.execute(
            select(AiChatMessage).where(AiChatMessage.user_id == user_id)
            .order_by(AiChatMessage.created_at.desc()).limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return messages
```

---

<a name="service-walkthrough"></a>
## 3. Service Method-by-Method Walkthrough

### Constructor — Wires All Dependencies

```python
def __init__(self, session: AsyncSession, redis_client: redis.Redis):
    self.session = session
    self.redis = redis_client
    self.llm = get_llm_client()               # Cached LLM (Ollama/Groq/OpenAI)
    self.token_tracker = TokenTracker(redis_client)  # Daily usage limits
```
- `get_llm_client()` — from the factory (Part 08b). Returns the configured provider
- `TokenTracker` — from Part 08c. Counts daily token usage per user in Redis
- Every public method uses these shared dependencies

### `chat()` — Dual Mode Chat

```python
async def chat(self, user_id, user_name, message, use_agent=True) -> str:
    # 1. Check daily token limit
    allowed, remaining = await self.token_tracker.check_limit(str(user_id))
    if not allowed:
        return "You've reached your daily AI usage limit."

    # 2. Save user message to DB
    await self._save_chat_message(user_id, "user", message, 0)

    # 3. Route to agent or direct
    if use_agent:
        response = await self._agent_chat(user_id, user_name, message)
    else:
        response = await self._direct_chat(user_id, user_name, message)

    # 4. Save assistant response to DB
    await self._save_chat_message(user_id, "assistant", response, 0)
    await self.session.commit()
    return response
```

**Token limit check FIRST** — before any LLM call. If the user hit 50K daily tokens, return a friendly message without calling the LLM (saves money).

**Save BOTH messages** — user question AND assistant response go into `ai_chat_messages`. This enables: chat history display, conversation context for future messages, and usage analytics.

### `stream_chat()` — SSE Word-by-Word

```python
async def stream_chat(self, user_id, user_name, message) -> AsyncGenerator[str, None]:
    # Build messages (system + history + user)
    messages = [system_prompt, ...history..., user_message]

    full_response = ""
    async for chunk in self.llm.stream_chat(messages):
        full_response += chunk  # Accumulate for saving
        yield chunk              # Send to client immediately

    # After streaming completes, save the full response
    await self._save_chat_message(user_id, "assistant", full_response, 0)
```

**`yield chunk`** — this is what makes it an **async generator**. Each `yield` sends one text chunk to the router, which wraps it as an SSE event. The client receives it immediately.

**`full_response += chunk`** — we accumulate the full text WHILE streaming. After the stream ends, we save the complete response to the database. The user sees text appearing word-by-word, AND the full response is persisted.

**Direct mode only** — streaming doesn't support agent mode because tool calls happen BETWEEN tokens (the agent pauses to run a tool, then resumes generating text). SSE expects a continuous stream.

### `upload_document()` — Full RAG Ingestion in One Method

```python
async def upload_document(self, user_id, filename, file_type, file_content, file_size) -> Document:
    # 1. Create document record (status: processing)
    doc = Document(status="processing", ...)
    self.session.add(doc)

    try:
        # 2. Extract text
        processed = DocumentProcessor().process(file_content, filename, file_type)

        # 3. Chunk text
        chunks = TextChunker(chunk_size=2000, chunk_overlap=200).chunk_text(processed.text)

        # 4. Generate embeddings
        embeddings = await EmbeddingGenerator().embed_texts([c.text for c in chunks])

        # 5. Store in pgvector
        for chunk, embedding in zip(chunks, embeddings):
            await VectorStore(self.session).store_chunk(...)

        # 6. Update status → processed
        doc.status = "processed"
        doc.chunk_count = len(chunks)

    except Exception as e:
        # 7. On error → update status → failed
        doc.status = "failed"
        doc.error_message = str(e)[:500]
```

This single method runs the ENTIRE RAG ingestion pipeline from Part 09. All 4 steps (extract → chunk → embed → store) happen in one transaction. If any step fails, the document is marked as "failed" with the error message — not abandoned in a "processing" limbo.

### `generate_weekly_report()` — Workflow in One Method

```python
async def generate_weekly_report(self, user_id, user_name) -> AiInsight:
    # Step 1: Collect data (DB queries, no LLM)
    data_summary = await DataCollector(self.session, user_id).collect()

    # Step 2: Analyze (LLM, temp=0.4)
    analysis, analysis_tokens = await Analyzer(self.llm).analyze(data_summary)

    # Step 3: Write report (LLM, temp=0.6)
    report, report_tokens = await ReportWriter(self.llm, user_name).write(data_summary, analysis)

    # Save as AI insight
    insight = AiInsight(insight_type="weekly_report", content=report, ...)
```

This calls the three weekly report steps from Part 11a directly. In production, the `WorkflowOrchestrator` with retry logic would wrap these calls. Here, the service keeps it simple for the API endpoint — orchestrator is used by Lambda for batch processing.

---

<a name="router"></a>
## 4. File 2: `router.py` — 9 Endpoints + SSE

### Type This Code: `backend/app/modules/ai/router.py`

*(Full source code — type from the actual file. Key endpoints shown with detailed explanation below.)*

The router file is ~220 lines. Type the entire file from the source at `backend/app/modules/ai/router.py`. Here are the most important parts explained:

---

<a name="router-walkthrough"></a>
## 5. Router Key Endpoints Explained

### SSE Streaming Endpoint — The Most Complex

```python
@router.get("/chat/stream", summary="Stream AI chat response (SSE)")
async def stream_chat(
    message: str,                                      # Query parameter (not body!)
    user_info: tuple[UUID, str] = Depends(get_user_name),
    service: AiService = Depends(get_ai_service),
) -> StreamingResponse:

    user_id, user_name = user_info

    async def event_generator():
        async for chunk in service.stream_chat(user_id, user_name, message):
            yield f"data: {chunk}\n\n"     # SSE format: "data: <text>\n\n"
        yield "data: [DONE]\n\n"           # Signal: stream complete

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",      # Tell Nginx: don't buffer!
        },
    )
```

**Why `GET` not `POST`?** `EventSource` (browser SSE API) only supports GET. The message is passed as a query parameter: `GET /ai/chat/stream?message=How's my sleep?`

**`async def event_generator()`** — A nested async generator. It wraps each text chunk from the LLM in SSE format (`data: <text>\n\n`) and yields it. FastAPI's `StreamingResponse` sends each yielded value to the client immediately.

**Three critical headers:**
- `Cache-Control: no-cache` — browsers must not cache SSE responses
- `Connection: keep-alive` — keep the HTTP connection open for streaming
- `X-Accel-Buffering: no` — Nginx-specific: don't collect chunks before forwarding. Without this, Nginx buffers the entire response and sends it at once — defeating the purpose of streaming

### File Upload Endpoint

```python
@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="PDF, TXT, or MD file"),
    user_id: UUID = Depends(get_current_user_id),
    service: AiService = Depends(get_ai_service),
) -> DocumentResponse:
    filename = file.filename or "unknown"
    file_type = filename.rsplit(".", 1)[-1].lower()

    content = await file.read()     # Read file bytes into memory
    file_size = len(content)

    doc = await service.upload_document(
        user_id=user_id, filename=filename, file_type=file_type,
        file_content=content, file_size=file_size,
    )
    return DocumentResponse.model_validate(doc)
```

**`UploadFile = File(...)`** — FastAPI handles multipart form data natively. The client sends a POST with `Content-Type: multipart/form-data` and the file as a form field.

**`await file.read()`** — reads the entire file into memory as bytes. For large files (>100MB), you'd stream to S3 instead. For health documents (typically <10MB), in-memory is fine.

**`filename.rsplit(".", 1)[-1]`** — extracts the file extension: `"Sleep Guide.pdf"` → `"pdf"`. `rsplit` splits from the right, `[-1]` takes the last part.

### Weekly Report Endpoint

```python
@router.post("/weekly-report", status_code=status.HTTP_201_CREATED)
async def generate_weekly_report(
    user_info: tuple[UUID, str] = Depends(get_user_name),
    service: AiService = Depends(get_ai_service),
) -> InsightResponse:
    user_id, user_name = user_info
    insight = await service.generate_weekly_report(user_id, user_name)
    return InsightResponse.model_validate(insight)
```

**`Depends(get_user_name)`** — A custom dependency that returns BOTH user_id AND user_name. The weekly report needs the user's name for personalization ("Hi Shreya! 🎉"). Other endpoints only need user_id.

### `get_user_name` Dependency

```python
async def get_user_name(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> tuple[UUID, str]:
    auth_service = AuthService(session, redis_client)
    user = await auth_service.get_current_user(user_id)
    return user_id, user.full_name
```

This is a **dependency chain**: `get_user_name` depends on `get_current_user_id` (which decodes JWT) and then fetches the user's name from the database. FastAPI resolves the entire chain automatically.

---

<a name="connections"></a>
## 6. How Service and Router Connect

```
POST /ai/chat {"message": "How's my sleep?", "use_agent": true}
  │
  ├── Router: Pydantic validates → ChatRequest
  ├── Depends: get_current_user_id → JWT decode → user_id
  ├── Depends: get_user_name → fetch user.full_name
  ├── Depends: get_ai_service → AiService(session, redis)
  │
  ▼
  service.chat(user_id, "Shreya", "How's my sleep?", use_agent=True)
  │
  ├── token_tracker.check_limit() → allowed (under 50K daily)
  ├── _save_chat_message(user_id, "user", "How's my sleep?")
  ├── _agent_chat() → HealthCoachAgent.create() → agent.chat()
  │                    ├── ReAct loop (Part 10c)
  │                    ├── [tool: query_logs] → sleep data for 7 days
  │                    ├── [tool: get_analytics] → weekly summary
  │                    └── Final answer: "Your sleep averaged 6.8h..."
  ├── _save_chat_message(user_id, "assistant", "Your sleep averaged...")
  ├── token_tracker.track_usage(user_id, input_tokens, output_tokens)
  └── session.commit()
  │
  ▼
  Router returns: {"response": "Your sleep averaged 6.8 hours this week..."}
```

---

<a name="verify"></a>
## 7. How to Verify Your Work

```bash
# Verify imports
docker-compose exec backend python -c "
from app.modules.ai.service import AiService
from app.modules.ai.router import router
print(f'Service methods: {[m for m in dir(AiService) if not m.startswith(\"_\") and callable(getattr(AiService, m, None))]}')
print(f'Router routes: {len(router.routes)} endpoints')
print('✅ AI service and router import OK')
"

# Test chat endpoint
TOKEN=\$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"shreya@test.com","password":"Test123!@#"}' | jq -r '.access_token')

curl -X POST http://localhost/api/v1/ai/chat \
  -H "Authorization: Bearer \$TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"How are my habits going?","use_agent":true}'

# Test SSE streaming
curl -N "http://localhost/api/v1/ai/chat/stream?message=Hello" \
  -H "Authorization: Bearer \$TOKEN"
# Should see: data: Hello\n\ndata: !\n\ndata: [DONE]\n\n
```

---

<a name="what-you-learned"></a>
## 8. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Cross-layer orchestration** | One service method calls LLM + RAG + Agent + Workflow | All service methods |
| 2 | **`AsyncGenerator[str, None]`** | Async generator for SSE streaming | `stream_chat()` |
| 3 | **`yield` in service** | Send chunk to client while continuing to generate | `stream_chat()` |
| 4 | **`StreamingResponse`** | FastAPI response that sends chunks over time | Router stream endpoint |
| 5 | **`media_type="text/event-stream"`** | HTTP content type for SSE | Stream response headers |
| 6 | **`X-Accel-Buffering: no`** | Tell Nginx to forward chunks immediately | Stream response headers |
| 7 | **`UploadFile = File(...)`** | FastAPI multipart file upload handling | Document upload endpoint |
| 8 | **`await file.read()`** | Read uploaded file bytes into memory | Upload handler |
| 9 | **Token limit check** | `check_limit()` before every LLM call | `chat()` first line |
| 10 | **Dual dependencies** | `get_user_name` returns `(user_id, name)` tuple | Report + chat endpoints |
| 11 | **Status update in try/except** | `processed` on success, `failed` on error | `upload_document()` |
| 12 | **`messages.reverse()`** | DB returns newest-first, LLM needs oldest-first | `_get_recent_messages()` |

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: How does the AI service orchestrate all the different AI features?
**A:** "The AiService is the single entry point for all AI features. It holds shared dependencies: database session, Redis client, LLM client (from factory), and token tracker. Chat routing: `use_agent=True` creates a HealthCoachAgent with ReAct loop and 5 tools; `use_agent=False` makes a single direct LLM call with conversation history. Document upload runs the full RAG pipeline in one transaction. Weekly report calls the 3-step workflow. Token tracking wraps every LLM call to enforce daily limits. The router never talks to agents or LLM clients directly."

### Q2: How does SSE streaming work end-to-end?
**A:** "The browser opens `EventSource('/ai/chat/stream?message=...')` — a long-lived GET connection. The router creates an `event_generator()` — an async generator that wraps each LLM chunk in SSE format (`data: <text>\\n\\n`). FastAPI's `StreamingResponse` sends each yielded event immediately. Nginx is configured with `proxy_buffering off` to forward without collecting. The LLM's `stream_chat()` is also an async generator — it yields tokens as the model generates them. Three async generators chained: LLM → service → router → client."

### Q3: How do you handle file uploads for RAG?
**A:** "FastAPI's `UploadFile` handles multipart form data. We read the file into memory (`await file.read()`), extract the file type from the filename, then pass everything to the service. The service creates a `Document` record with status 'processing', then runs the RAG pipeline: extract text (PyPDF2), chunk (recursive splitter), embed (LLM API), store (pgvector). On success: `status='processed'`. On any error: `status='failed'` with the error message. The entire pipeline is in a try/except so the document record always reflects the true state."

### Q4: Why save the full response AFTER streaming completes?
**A:** "During streaming, we `yield` each chunk to the client AND accumulate it in `full_response`. After the stream ends (LLM finished generating), we save the complete response to `ai_chat_messages`. We can't save before streaming because we don't know the full text yet. We can't save during streaming because each chunk is only a few tokens. So we accumulate, then save once at the end. The trade-off: if the connection drops mid-stream, the partial response isn't saved. For a health tracker, this is acceptable."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 12a: AI Models & Schemas](./phase4-part12a-ai-models-schemas.md) |
| ➡️ Next | [Phase 4 Part 12c: AI Migration & Architecture](./phase4-part12c-ai-migration.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Part 12 Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 12a | ✅ Done | AI Models & Schemas |
| **12b** | ✅ **You are here** | AI Service & Router |
| 12c | ⬜ Next | AI Migration & Architecture |

---

**End of Phase 4 Part 12b: AI Service & Router**

*The largest service and the most feature-rich router in the project. 7 service methods orchestrate LLM, RAG, agents, and workflows. 9 endpoints expose everything including SSE streaming and file upload. Next: the migration that creates the 4 AI tables with pgvector.*
