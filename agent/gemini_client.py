"""
Wrapper around the Qwen API with built-in retry logic.
Handles all LLM API calls with automatic exponential backoff retry.
"""

import time
from openai import OpenAI

from config.settings import Settings


class GeminiClient:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
        )

    def generate(self, prompt: str, system: str = "") -> str:
        """Send a prompt to Qwen and return the response text.

        Args:
            prompt: The user-facing prompt or question.
            system: Optional system instruction that sets the LLM's behavior
                    (e.g., "You are a financial analyst"). Sent as a separate
                    field so Qwen treats it as a system prompt, not user input.

        Returns:
            The LLM's response as a string.
        """
        #
        # Low temperature = factual, high = creative. Financial data needs low.
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self.settings.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.llm_model,
                    messages=messages,
                    temperature=self.settings.llm_temperature,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                # Only retry on rate limit errors (429 / RESOURCE_EXHAUSTED).
                # Other errors (bad API key, network down) are re-raised immediately
                # since retrying won't fix them.
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    # Exponential backoff: wait 10s, 20s, 40s, 80s, 120s, 120s...
                    # Doubling prevents all users from retrying at the same time.
                    # min() caps the wait at retry_max_delay (120s).
                    wait = min(
                        2 ** attempt * self.settings.retry_base_delay,
                        self.settings.retry_max_delay,
                    )
                    print(f"  Rate limited. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise

        # All retries exhausted. FastAPI endpoints catch this and return a
        # user-friendly message ("Please wait 1-2 minutes and try again.").
        raise RuntimeError("Max retries reached — Qwen quota exhausted.")

    @staticmethod
    def strip_markdown_fences(text: str) -> str:
        """Remove markdown code fences from LLM response.
        Args:
            text: Raw response text from the model.

        Returns:
            The text with markdown fences removed, if present.
        """
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return text.strip()
