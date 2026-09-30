# ============================================================================
# Agent Tools — Abstract Base Tool
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the interface that ALL agent tools must implement.
#   A tool is a function the AI agent can call to fetch real data.
#
# HOW TOOLS WORK IN AN AGENT:
#   1. LLM sees the tool's name, description, and parameter schema
#   2. LLM decides: "I need to check the user's sleep data"
#   3. LLM outputs a tool call: {"name": "query_logs", "arguments": {...}}
#   4. Agent executes the tool → gets real data from the database
#   5. Agent feeds the tool result back to the LLM
#   6. LLM generates a response using the real data
#
# TOOL DEFINITION FORMAT:
#   Same format as OpenAI function calling:
#   {
#       "type": "function",
#       "function": {
#           "name": "query_logs",
#           "description": "Get habit log data for a date range",
#           "parameters": {
#               "type": "object",
#               "properties": {
#                   "habit_name": {"type": "string"},
#                   "days": {"type": "integer"}
#               }
#           }
#       }
#   }
#
#   This format is universal — works with OpenAI, Groq, Ollama, Anthropic.
# ============================================================================

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.

    Every tool must define:
    - name: unique identifier (e.g., "query_logs")
    - description: what the tool does (LLM reads this to decide when to use it)
    - parameters_schema: JSON Schema for the tool's parameters
    - execute(): the actual function that runs when the tool is called

    DESIGN NOTE:
        The LLM only sees name, description, and parameters_schema.
        It doesn't see the execute() code — just the "API contract."
        A good description is critical — if the LLM doesn't understand
        what the tool does, it won't know when to use it.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (lowercase, underscored)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """
        What this tool does — the LLM reads this to decide when to use it.
        Be specific: "Get the user's habit log data for a specific date range"
        Not vague: "Get data"
        """
        ...

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """
        JSON Schema defining the tool's parameters.
        The LLM uses this to generate valid arguments.
        """
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool with the given arguments.

        Returns a string that will be fed back to the LLM as the tool result.
        The string should be human-readable — the LLM will interpret it
        and use the information in its response.

        Returns:
            A string describing the tool's output (data, results, etc.)
        """
        ...

    def to_openai_schema(self) -> dict:
        """
        Convert this tool to OpenAI function calling format.

        This format is the industry standard — used by OpenAI, Groq,
        Ollama, and most other LLM providers.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }
