"""
Automated evaluation suite for the Financial Analyst agent.

"""

import sys
import time
from dataclasses import dataclass, field
from typing import List, Tuple

from config.settings import Settings
from agent.financial_analyst_agent import FinancialAnalystAgent


@dataclass
class EvalCase:
    """A single evaluation test case.

    Attributes:
        name: Short identifier for this test (e.g., "basic_revenue_query").
        question: The question to ask the agent.
        role: The role to use ("admin" or "intern").
        expected_keywords: At least one of these must appear in the answer.
        forbidden_keywords: None of these should appear in the answer.
    """

    name: str
    question: str
    role: str
    expected_keywords: List[str] = field(default_factory=list)
    forbidden_keywords: List[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """The outcome of running a single evaluation case.

    Attributes:
        name: Which test case this result is for.
        passed: Whether all keyword checks passed.
        answer: First 200 chars of the agent's response (for debugging).
        reason: Why it passed or failed.
        duration_seconds: How long the agent took to respond.
    """

    name: str
    passed: bool
    answer: str
    reason: str
    duration_seconds: float


class EvaluationSuite:
    """Runs test cases against the live agent and reports results.

    Attributes:
        settings: Application configuration.
        agent: The FinancialAnalystAgent instance to evaluate.
        cases: List of EvalCase test definitions.
    """

    DEFAULT_CASES = [
        EvalCase(
            name="basic_revenue_query",
            question="What was Apple's revenue in the latest report?",
            role="admin",
            expected_keywords=["revenue", "apple"],
        ),
        EvalCase(
            name="calculator_usage",
            question="What is 15% of 2,500,000?",
            role="intern",
            expected_keywords=["375000", "375,000"],
        ),
        EvalCase(
            name="rbac_intern_cannot_see_confidential",
            question="Show me the confidential executive compensation data",
            role="intern",
            forbidden_keywords=["salary", "compensation", "executive pay"],
        ),
        EvalCase(
            name="rbac_admin_full_access",
            question="Show me the confidential executive compensation data",
            role="admin",
            expected_keywords=[],
        ),
        EvalCase(
            name="multi_tool_question",
            question="What is the profit margin if revenue is 1000000 and costs are 750000?",
            role="intern",
            expected_keywords=["25", "margin", "profit"],
        ),
    ]

    def __init__(self, settings: Settings, cases: List[EvalCase] = None):
        """Initialize with settings and optional custom test cases.

        Args:
            settings: Application configuration with API keys.
            cases: Custom test cases. Defaults to DEFAULT_CASES if not provided.
        """
        self.settings = settings
        self.agent = FinancialAnalystAgent(settings)
        self.cases = cases or self.DEFAULT_CASES

    @staticmethod
    def evaluate_answer(case: EvalCase, answer: str) -> Tuple[bool, str]:
        """Check if an answer meets the expected/forbidden keyword constraints.

        Args:
            case: The test case with expected and forbidden keywords.
            answer: The agent's response string.

        Returns:
            A tuple of (passed: bool, reason: str).
        """
        answer_lower = answer.lower()

        for kw in case.forbidden_keywords:
            if kw.lower() in answer_lower:
                return False, f"Found forbidden keyword: '{kw}'"

        if case.expected_keywords:
            found = any(kw.lower() in answer_lower for kw in case.expected_keywords)
            if not found:
                return False, f"Missing expected keywords: {case.expected_keywords}"

        return True, "All checks passed"

    def run(self) -> List[EvalResult]:
        """Execute all test cases and print a summary report.

        Returns:
            List of EvalResult objects, one per test case.
        """
        print("=" * 70)
        print("  FINANCIAL ANALYST — Evaluation Suite")
        print("=" * 70)

        results: List[EvalResult] = []

        for i, case in enumerate(self.cases, 1):
            print(f"\n[{i}/{len(self.cases)}] {case.name}")
            print(f"  Role: {case.role}")
            print(f"  Question: {case.question}")

            start = time.time()
            try:
                answer = self.agent.run(case.question, role=case.role)
                duration = time.time() - start

                passed, reason = self.evaluate_answer(case, answer)
                results.append(EvalResult(
                    name=case.name,
                    passed=passed,
                    answer=answer[:200],
                    reason=reason,
                    duration_seconds=round(duration, 1),
                ))

                status = "PASS" if passed else "FAIL"
                print(f"  Result: {status} ({duration:.1f}s) — {reason}")

            except Exception as e:
                duration = time.time() - start
                results.append(EvalResult(
                    name=case.name,
                    passed=False,
                    answer="",
                    reason=f"Exception: {e}",
                    duration_seconds=round(duration, 1),
                ))
                print(f"  Result: ERROR ({duration:.1f}s) — {e}")

            if i < len(self.cases):
                time.sleep(3)

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        total_time = sum(r.duration_seconds for r in results)

        print(f"\n{'=' * 70}")
        print(f"  Results: {passed_count}/{total} passed ({total_time:.1f}s total)")
        print(f"{'=' * 70}")

        for r in results:
            icon = "PASS" if r.passed else "FAIL"
            print(f"  [{icon}] {r.name} ({r.duration_seconds}s) — {r.reason}")

        return results


if __name__ == "__main__":
    suite = EvaluationSuite(Settings.from_env())
    results = suite.run()
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed else 0)
