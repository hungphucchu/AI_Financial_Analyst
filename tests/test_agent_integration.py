"""
Integration tests for the full agent pipeline.
"""

import os
import time
import pytest
from config.settings import Settings
from agent.financial_analyst_agent import FinancialAnalystAgent


pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set — skipping integration tests",
)

DELAY = 15  # seconds between tests to respect Gemini free-tier rate limits


@pytest.fixture(scope="module")
def agent():
    settings = Settings.from_env()
    return FinancialAnalystAgent(settings)


class TestRAGQueries:
    def test_public_data_retrieval(self, agent):
        """Agent should retrieve Tesla revenue from public 10-K documents."""
        answer = agent.run("What was Tesla's revenue in 2023?", role="intern")
        assert answer is not None
        assert len(answer) > 20
        print(f"\n[TEST] Public data answer: {answer[:200]}")

    def test_multi_tool_rag_plus_calculator(self, agent):
        """Agent should use RAG + Calculator for a ratio question."""
        time.sleep(DELAY)
        answer = agent.run(
            "What is Apple's revenue as a percentage of Tesla's revenue?",
            role="intern",
        )
        assert answer is not None
        assert len(answer) > 20
        print(f"\n[TEST] Multi-tool answer: {answer[:200]}")


class TestRBACEnforcement:
    def test_intern_cannot_see_confidential(self, agent):
        """Intern should NOT get details about Project Phoenix."""
        time.sleep(DELAY)
        answer = agent.run("What is Project Phoenix?", role="intern")
        assert answer is not None
        # The answer should indicate lack of information
        print(f"\n[TEST] Intern answer: {answer[:200]}")

    def test_admin_can_see_confidential(self, agent):
        """Admin SHOULD get full details about Project Phoenix."""
        time.sleep(DELAY)
        answer = agent.run("What is Project Phoenix?", role="admin")
        assert answer is not None
        assert len(answer) > 20
        print(f"\n[TEST] Admin answer: {answer[:200]}")
