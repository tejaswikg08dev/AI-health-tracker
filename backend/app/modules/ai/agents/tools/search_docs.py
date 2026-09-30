# ============================================================================
# Agent Tool — Search Documents (RAG)
# ============================================================================
# WHEN THE AGENT USES IT: "What does my blood report say about iron?"
#   Agent thinks: "I need to search the user's documents" → calls this tool
#   Tool runs the full RAG retrieval pipeline → returns relevant chunks
# ============================================================================

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.ai.rag.retriever import Retriever


class SearchDocsTool(BaseTool):
    """Search user's uploaded documents using RAG vector similarity search."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def description(self) -> str:
        return (
            "Search through the user's uploaded health documents (blood reports, "
            "nutrition guides, doctor's notes) to find relevant information. "
            "Use this when the user asks about their medical reports, "
            "health guidelines, or document-specific information."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query describing what information to find "
                                   "(e.g., 'iron levels', 'cholesterol recommendations')",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return "No search query provided."

        retriever = Retriever(self.session)
        context = await retriever.retrieve(
            query=query,
            user_id=str(self.user_id),
            top_k=3,
        )

        if not context.formatted_context:
            return (
                "No relevant information found in your documents. "
                "You can upload health documents (PDFs, text files) for me to reference."
            )

        return context.formatted_context
