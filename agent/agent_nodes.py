"""
The three LangGraph node functions: Planner, Tool Executor, Synthesizer.

How the pipeline works:
    1. Planner: Asks Gemini "which tools should I use for this question?"
       → outputs a JSON plan like {"tools": [{"name": "RAG_SEARCH", "input": "..."}]}

    2. Tool Executor: Parses the plan, runs each tool, collects results
       → outputs {"rag_search": "Tesla revenue was $96.8B...", "calculator": "25.24"}

    3. Synthesizer: Gives all tool results to Gemini and asks for a final answer
       → outputs a polished professional response
"""

import json
import time

from agent.agent_state import AgentState
from agent.prompts import PLANNER_SYSTEM_PROMPT, SYNTHESIZER_SYSTEM_PROMPT
from agent.gemini_client import GeminiClient
from config.settings import Settings
from tools.base_tool import BaseTool


class AgentNodes:

    def __init__(self, llm: GeminiClient, tools: dict, settings: Settings):
        self.llm = llm
        self.tools = tools
        self.settings = settings

    def planner(self, state: AgentState) -> dict:
        """Decide which tools to call for the user's question.

        Args:
            state: Must contain ``query`` (the user's question).

        Returns:
            Dict with ``plan`` (JSON string) and ``iteration`` (incremented).
        """
        print("\n[Planner] Analyzing query...")

        raw = self.llm.generate(
            prompt=f"User query: {state['query']}",
            system=PLANNER_SYSTEM_PROMPT,
        )
        plan = GeminiClient.strip_markdown_fences(raw)

        print(f"  Plan: {plan[:200]}")
        return {"plan": plan, "iteration": state.get("iteration", 0) + 1}

    def tool_executor(self, state: AgentState) -> dict:
        """Run the tools specified in the planner's JSON plan.

        Args:
            state: Must contain ``plan`` (JSON from planner) and ``role``.

        Returns:
            Dict with ``tool_outputs`` mapping tool names to result strings.
        """
        print("\n[Tool Executor] Running tools...")
        outputs: dict = {}

        try:
            plan_data = json.loads(state["plan"])
            tools_to_run = plan_data.get("tools", [])
        except (json.JSONDecodeError, KeyError) as e:
            return {"tool_outputs": {"error": f"Plan parse failed: {e}"}}

        for spec in tools_to_run:
            tool_name = spec.get("name", "")
            tool_input = spec.get("input", "")

            tool = self.tools.get(tool_name)
            if tool is None:
                outputs[tool_name] = f"Unknown tool: {tool_name}"
                continue

            print(f"  Running {tool_name}: '{tool_input}'")
            outputs[tool_name.lower()] = tool.execute(
                tool_input, role=state["role"]
            )
            time.sleep(self.settings.inter_tool_delay)

        print(f"  Completed: {list(outputs.keys())}")
        return {"tool_outputs": outputs}

    def synthesizer(self, state: AgentState) -> dict:
        """Combine all tool outputs into a professional final answer.

        Args:
            state: Must contain ``query`` and ``tool_outputs``.

        Returns:
            Dict with ``final_answer`` — the response shown to the user.
        """
        print("\n[Synthesizer] Generating response...")

        role = state.get("role", "intern")
        tool_text = "\n\n".join(
            f"[{name.upper()}]: {output}"
            for name, output in state["tool_outputs"].items()
        )

        role_context = (
            f"The user's role is: {role}. "
            f"{'They have full access to all documents including confidential ones.' if role == 'admin' else 'They only have access to PUBLIC documents. Confidential memos, CEO communications, and internal strategy docs are restricted to admin users.'}"
        )

        answer = self.llm.generate(
            prompt=f"User question: {state['query']}\n\n{role_context}\n\nTool outputs:\n{tool_text}",
            system=SYNTHESIZER_SYSTEM_PROMPT,
        )
        return {"final_answer": answer}
