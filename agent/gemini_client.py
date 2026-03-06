"""
Wrapper around the Google Gemini API with built-in retry logic.
Handles all Gemini API calls with automatic exponential backoff retry.

"""

import time
import google.genai

from config.settings import Settings


class GeminiClient:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = google.genai.Client(api_key=settings.google_api_key)

    def generate(self, prompt: str, system: str = "") -> str:
        """Send a prompt to Gemini and return the response text.

        Args:
            prompt: The user-facing prompt or question.
            system: Optional system instruction that sets the LLM's behavior
                    (e.g., "You are a financial analyst"). Sent as a separate
                    field so Gemini treats it as a system prompt, not user input.

        Returns:
            The LLM's response as a string.
        """
        config = {"temperature": self.settings.llm_temperature}
        if system:
            config["system_instruction"] = system

        for attempt in range(self.settings.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.settings.llm_model,
                    contents=prompt,
                    config=config,
                )
                return response.text
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = min(
                        2 ** attempt * self.settings.retry_base_delay,
                        self.settings.retry_max_delay,
                    )
                    print(f"  Rate limited. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError("Max retries reached — Gemini quota exhausted.")

    @staticmethod
    def strip_markdown_fences(text: str) -> str:
        """Remove markdown code fences from Gemini's response.
        Args:
            text: Raw response text from Gemini.

        Returns:
            The text with markdown fences removed, if present.
        """
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return text.strip()
