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
from app.modules.ai.workflows.orchestrator import WorkflowOrchestrator
from app.modules.ai.workflows.weekly_report.analyzer import Analyzer
from app.modules.ai.workflows.weekly_report.data_collector import DataCollector
from app.modules.ai.workflows.weekly_report.report_writer import ReportWriter
from app.modules.ai.workflows.base_workflow import BaseWorkflow, StepResult
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.habits.repository import HabitRepository
from app.modules.logs.repository import LogRepository
from app.shared.date_utils import days_ago, today_utc
from app.shared.logging import get_logger

logger = get_logger(__name__)


class AiService:
    """
    AI service — orchestrates chat, RAG, agents, and workflows.

    All AI features go through this service.
    The router never talks to LLM clients or agents directly.
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
        self,
        user_id: UUID,
        user_name: str,
        message: str,
        use_agent: bool = True,
    ) -> str:
        """
        Chat with the AI health coach.

        Two modes:
        - Agent mode (use_agent=True): ReAct agent with tool calling.
          Slower but much smarter — can fetch real data.
        - Direct mode (use_agent=False): Single LLM call.
          Faster but can only use conversation context, no data fetching.
        """
        # Check token limit
        allowed, remaining = await self.token_tracker.check_limit(str(user_id))
        if not allowed:
            return "You've reached your daily AI usage limit. Try again tomorrow!"

        # Save user message to DB
        await self._save_chat_message(user_id, "user", message, 0)

        if use_agent:
            response = await self._agent_chat(user_id, user_name, message)
        else:
            response = await self._direct_chat(user_id, user_name, message)

        # Save assistant response to DB
        await self._save_chat_message(user_id, "assistant", response, 0)
        await self.session.commit()

        return response

    async def stream_chat(
        self,
        user_id: UUID,
        user_name: str,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response word by word using SSE.

        Only supports direct mode (no agent) because tool calls
        happen between tokens and can't be streamed linearly.
        For agent mode, use the non-streaming chat() method.
        """
        # Save user message
        await self._save_chat_message(user_id, "user", message, 0)

        # Build messages with context
        habits_repo = HabitRepository(self.session)
        habits = await habits_repo.get_user_habits(user_id)

        system = HEALTH_COACH_SYSTEM.render(
            user_name=user_name,
            timezone="UTC",
            habit_count=len(habits),
        )

        # Get recent chat history for context
        history = await self._get_recent_messages(user_id, limit=10)

        messages = [LLMMessage(role="system", content=system)]
        for msg in history:
            messages.append(LLMMessage(role=msg.role, content=msg.content))
        messages.append(LLMMessage(role="user", content=message))

        # Stream from LLM
        full_response = ""
        async for chunk in self.llm.stream_chat(messages):
            full_response += chunk
            yield chunk

        # Save full response after streaming completes
        await self._save_chat_message(user_id, "assistant", full_response, 0)
        await self.session.commit()

    async def get_chat_history(self, user_id: UUID, limit: int = 50) -> list[AiChatMessage]:
        """Get recent chat messages for the user."""
        return await self._get_recent_messages(user_id, limit)

    # ══════════════════════════════════════════════════════════════════
    # DOCUMENTS (RAG)
    # ══════════════════════════════════════════════════════════════════

    async def upload_document(
        self,
        user_id: UUID,
        filename: str,
        file_type: str,
        file_content: bytes,
        file_size: int,
    ) -> Document:
        """
        Upload and process a document for RAG.

        Pipeline: upload → extract text → chunk → embed → store vectors
        """
        # Create document record
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            status="processing",
        )
        self.session.add(doc)
        await self.session.flush()

        try:
            # Step 1: Extract text
            processor = DocumentProcessor()
            processed = processor.process(file_content, filename, file_type)
            doc.page_count = processed.page_count

            # Step 2: Chunk text
            chunker = TextChunker(chunk_size=2000, chunk_overlap=200)
            chunks = chunker.chunk_text(processed.text, processed.page_texts)

            if not chunks:
                doc.status = "failed"
                doc.error_message = "No text content could be extracted"
                await self.session.commit()
                return doc

            # Step 3: Generate embeddings
            embedder = EmbeddingGenerator()
            chunk_texts = [c.text for c in chunks]
            embeddings = await embedder.embed_texts(chunk_texts)

            # Step 4: Store chunks with embeddings in pgvector
            vector_store = VectorStore(self.session)
            for chunk, embedding in zip(chunks, embeddings):
                await vector_store.store_chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=str(doc_id),
                    user_id=str(user_id),
                    chunk_text=chunk.text,
                    chunk_index=chunk.index,
                    page_number=chunk.page_number,
                    token_count=chunk.token_count,
                    embedding=embedding,
                )

            doc.status = "processed"
            doc.chunk_count = len(chunks)
            await self.session.commit()

            logger.info(
                "document_processed",
                doc_id=str(doc_id),
                filename=filename,
                chunks=len(chunks),
            )

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)[:500]
            await self.session.commit()
            logger.error("document_processing_error", filename=filename, error=str(e))

        return doc

    async def get_documents(self, user_id: UUID) -> list[Document]:
        """Get all documents for a user."""
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, user_id: UUID, document_id: UUID) -> bool:
        """Delete a document and all its chunks/embeddings."""
        # Delete chunks first (foreign key constraint)
        await self.session.execute(
            sa_delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        # Delete document
        result = await self.session.execute(
            sa_delete(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    # ══════════════════════════════════════════════════════════════════
    # INSIGHTS
    # ══════════════════════════════════════════════════════════════════

    async def generate_insight(self, user_id: UUID) -> AiInsight:
        """Generate an on-demand AI insight based on recent data."""
        # Collect recent data
        collector = DataCollector(self.session, user_id)
        data_summary = await collector.collect()

        # Generate insight via LLM
        prompt = INSIGHT_PROMPT.render(data_context=data_summary)
        response = await self.llm.chat(
            messages=[
                LLMMessage(role="system", content="Generate a brief, actionable health insight."),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.5,
            max_tokens=300,
        )

        # Save insight
        insight = AiInsight(
            user_id=user_id,
            insight_type="on_demand",
            title="Health Insight",
            content=response.content,
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
        """Get recent AI insights for a user."""
        result = await self.session.execute(
            select(AiInsight)
            .where(AiInsight.user_id == user_id)
            .order_by(AiInsight.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    # WEEKLY REPORT (Agentic Workflow)
    # ══════════════════════════════════════════════════════════════════

    async def generate_weekly_report(
        self, user_id: UUID, user_name: str
    ) -> AiInsight:
        """
        Run the full weekly report agentic workflow.

        Pipeline: DataCollector → Analyzer → ReportWriter
        Managed by the WorkflowOrchestrator with retry logic.
        """
        # Step 1: Collect data
        collector = DataCollector(self.session, user_id)
        data_summary = await collector.collect()

        # Step 2: Analyze
        analyzer = Analyzer(self.llm)
        analysis, analysis_tokens = await analyzer.analyze(data_summary)

        # Step 3: Write report
        writer = ReportWriter(self.llm, user_name)
        report, report_tokens = await writer.write(data_summary, analysis)

        total_tokens = analysis_tokens + report_tokens

        # Save as insight
        insight = AiInsight(
            user_id=user_id,
            insight_type="weekly_report",
            title=f"Weekly Report — {today_utc()}",
            content=report,
            tokens_used=total_tokens,
        )
        self.session.add(insight)
        await self.session.commit()
        await self.session.refresh(insight)

        await self.token_tracker.track_usage(str(user_id), total_tokens // 2, total_tokens // 2)

        logger.info(
            "weekly_report_generated",
            user_id=str(user_id),
            tokens=total_tokens,
        )

        return insight

    # ══════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════

    async def _agent_chat(self, user_id: UUID, user_name: str, message: str) -> str:
        """Run the Health Coach agent for a user message."""
        agent = await HealthCoachAgent.create(
            session=self.session,
            redis_client=self.redis,
            user_id=user_id,
            user_name=user_name,
        )
        response = await agent.chat(message)

        # Track tokens
        await self.token_tracker.track_usage(
            str(user_id), agent.total_tokens // 2, agent.total_tokens // 2
        )

        return response

    async def _direct_chat(self, user_id: UUID, user_name: str, message: str) -> str:
        """Direct LLM chat without agent tools."""
        habits_repo = HabitRepository(self.session)
        habits = await habits_repo.get_user_habits(user_id)

        system = HEALTH_COACH_SYSTEM.render(
            user_name=user_name,
            timezone="UTC",
            habit_count=len(habits),
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

    async def _save_chat_message(
        self, user_id: UUID, role: str, content: str, tokens: int
    ) -> None:
        """Save a chat message to the database."""
        msg = AiChatMessage(
            user_id=user_id,
            role=role,
            content=content,
            tokens_used=tokens,
        )
        self.session.add(msg)
        await self.session.flush()

    async def _get_recent_messages(self, user_id: UUID, limit: int = 10) -> list[AiChatMessage]:
        """Get the N most recent chat messages for context."""
        result = await self.session.execute(
            select(AiChatMessage)
            .where(AiChatMessage.user_id == user_id)
            .order_by(AiChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()  # Oldest first for conversation order
        return messages
