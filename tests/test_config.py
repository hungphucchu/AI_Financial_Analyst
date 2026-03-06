"""Unit tests for Settings configuration."""

import os
from unittest.mock import patch
import pytest
from config.settings import Settings


class TestSettingsDefaults:
    def test_default_model_names(self):
        s = Settings(google_api_key="test")
        assert s.llm_model == "gemini-2.0-flash"
        assert s.embedding_model == "gemini-embedding-001"

    def test_default_paths(self):
        s = Settings(google_api_key="test")
        assert s.chroma_db_path == "./chroma_db"
        assert s.data_public_dir == "./data/public"

    def test_default_retry_config(self):
        s = Settings(google_api_key="test")
        assert s.max_retries == 4
        assert s.retry_base_delay == 5
        assert s.retry_max_delay == 60


@patch("config.settings.load_dotenv")
class TestSettingsFromEnv:
    def test_raises_without_api_key(self, mock_dotenv, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            Settings.from_env()

    def test_loads_google_key(self, mock_dotenv, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-123")
        s = Settings.from_env()
        assert s.google_api_key == "test-key-123"

    def test_tavily_key_optional(self, mock_dotenv, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        s = Settings.from_env()
        assert s.tavily_api_key == ""
