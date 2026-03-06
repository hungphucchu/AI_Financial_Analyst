"""
Abstract base class that every tool must implement.
Interface that all agent tools must implement.

The agent's planner node sees ``name`` and ``description`` to decide
which tool to call, then the executor node calls ``execute()`` with
whatever input the planner generated.

Subclasses:
    - RAGTool: Searches internal documents with RBAC
    - CalculatorTool: Safe math evaluation
    - WebSearchTool: Real-time web data via Tavily

"""

from abc import ABC, abstractmethod


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier that the LLM planner outputs in its JSON plan.

        Example: "RAG_SEARCH", "CALCULATOR", "WEB_SEARCH"
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description shown to the LLM so it knows when to pick this tool.

        Keep it concise — the LLM reads this every request to decide which tools to use.
        """
        ...

    @abstractmethod
    def execute(self, tool_input: str, **kwargs) -> str:
        """Run the tool and return a result string.

        Args:
            tool_input: The query or expression to process (comes from the LLM planner).
            **kwargs: Extra context. The RAG tool uses ``role`` for RBAC filtering.

        Returns:
            A string result. Even errors should be returned as strings (not raised),
            so the synthesizer can explain what went wrong to the user.
        """
        ...
