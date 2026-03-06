"""
State schema for the LangGraph agent pipeline.
The state dictionary passed between all LangGraph nodes.

"""

from typing import TypedDict


class AgentState(TypedDict):
    """
    Attributes:
        query: The user's original question (set once, never modified).
        role: The user's access role — "admin" or "intern". Drives RBAC
              filtering in the RAG tool.
        plan: JSON string from the planner node specifying which tools
              to call and with what inputs. Example:
              ``{"tools": [{"name": "RAG_SEARCH", "input": "Tesla revenue"}]}``
        tool_outputs: Dictionary mapping tool names to their string results.
              Example: ``{"rag_search": "Tesla revenue was $96.8B..."}``
        final_answer: The synthesizer's polished response shown to the user.
        iteration: Counter for potential re-planning loops (reserved for future use).
    """

    query: str
    role: str
    plan: str
    tool_outputs: dict
    final_answer: str
    iteration: int
