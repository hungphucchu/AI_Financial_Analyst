"""
Prompt injection detection for the API layer.

"""

import re
from typing import Optional


class PromptGuardrail:
    """Scans user queries for prompt injection attacks before they reach the LLM.

    Attributes:
        PATTERNS: Raw regex strings for common prompt injection techniques.
        compiled_patterns: Pre-compiled regex objects for fast matching.
    """

    PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"disregard\s+(all\s+)?(previous|your)\s+",
        r"forget\s+(everything|all|your)\s+(you|instructions|rules)",
        r"override\s+(your|system|all)\s+",
        r"pretend\s+(you\s+are|to\s+be)\s+",
        r"act\s+as\s+(if|though)\s+you\s+(have\s+no|don't\s+have)\s+",
        r"system\s*prompt\s*:",
        r"<\s*system\s*>",
        r"jailbreak",
        r"DAN\s+mode",
        r"do\s+anything\s+now",
    ]

    def __init__(self):
        """Compile all regex patterns once at startup for fast matching."""
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.PATTERNS
        ]

    def check(self, query: str) -> Optional[str]:
        """Scan a query for prompt injection patterns.

        Args:
            query: The user's raw question text.

        Returns:
            A rejection message string if a prompt injection pattern was
            detected, or None if the query is clean and safe to process.
        """
        for pattern in self.compiled_patterns:
            if pattern.search(query):
                return (
                    "Your query was flagged as a potential prompt injection. "
                    "Please rephrase your question about financial data."
                )
        return None
