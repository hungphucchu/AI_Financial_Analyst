"""
Top-level agent that wires everything into a LangGraph pipeline.
Orchestrates the full agent pipeline: plan → execute → synthesize.

"""

from langgraph.graph import StateGraph, END

from agent.agent_state import AgentState
from agent.gemini_client import GeminiClient
from agent.agent_nodes import AgentNodes
from config.settings import Settings
from tools.rag_tool import RAGTool
from tools.calculator_tool import CalculatorTool
from tools.web_search_tool import WebSearchTool


class FinancialAnalystAgent:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = GeminiClient(settings)
        self.tools = self.register_tools()
        self.nodes = AgentNodes(self.llm, self.tools, settings)
        self.graph = self.build_graph()

    def register_tools(self) -> dict:
        """Create all tool instances and build a name → tool lookup dict.

        Returns:
            Dict mapping tool names (e.g., "RAG_SEARCH") to tool instances.
        """
        tool_instances = [
            RAGTool(self.settings),
            CalculatorTool(),
            WebSearchTool(self.settings),
        ]
        return {tool.name: tool for tool in tool_instances}

    def build_graph(self):
        """Construct the LangGraph with three nodes in a linear pipeline.

        Returns:
            A compiled LangGraph ready to invoke with a state dict.
        """
        graph = StateGraph(AgentState)

        graph.add_node("planner", self.nodes.planner)
        graph.add_node("tool_executor", self.nodes.tool_executor)
        graph.add_node("synthesizer", self.nodes.synthesizer)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "tool_executor")
        graph.add_edge("tool_executor", "synthesizer")
        graph.add_edge("synthesizer", END)

        return graph.compile()

    def run(self, query: str, role: str = "intern") -> str:
        """Process a user query through the full agent pipeline.

        Args:
            query: The user's question (e.g., "What was Tesla's revenue?").
            role: The user's access role — "admin" sees all documents,
                  "intern" (default) only sees public documents.

        Returns:
            The final synthesized answer as a string.
        """
        print(f"\n{'='*60}")
        print(f"Financial Analyst Agent")
        print(f"  Query: {query}")
        print(f"  Role:  {role}")
        print(f"{'='*60}")

        initial_state: AgentState = {
            "query": query,
            "role": role,
            "plan": "",
            "tool_outputs": {},
            "final_answer": "",
            "iteration": 0,
        }

        # Run the full pipeline: Planner → Tool Executor → Synthesizer.
        # Returns the final state dict with all fields filled in.
        result = self.graph.invoke(initial_state)
        return result["final_answer"]
