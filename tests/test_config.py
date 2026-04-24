"""Unit tests for Settings configuration."""

import os
from unittest.mock import patch
import pytest
from config.settings import Settings


class TestSettingsDefaults:
    def test_default_model_names(self):
        s = Settings(qwen_api_key="test")
        assert s.llm_model == "qwen-plus"
        assert s.embedding_model == "text-embedding-v3"

    def test_default_paths(self):
        s = Settings(qwen_api_key="test")
        assert s.chroma_db_path == "./chroma_db"
        assert s.data_public_dir == "./data/public"

    def test_default_retry_config(self):
        s = Settings(qwen_api_key="test")
        assert s.max_retries == 6
        assert s.retry_base_delay == 10
        assert s.retry_max_delay == 120


@patch("config.settings.load_dotenv")
class TestSettingsFromEnv:
    def test_raises_without_api_key(self, mock_dotenv, monkeypatch):
        monkeypatch.delenv("QWEN_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        with pytest.raises(ValueError, match="QWEN_API_KEY"):
            Settings.from_env()

    def test_loads_qwen_key(self, mock_dotenv, monkeypatch):
        monkeypatch.setenv("QWEN_API_KEY", "test-key-123")
        monkeypatch.setenv("QWEN_BASE_URL", "https://example.invalid/v1")
        monkeypatch.setenv("QWEN_MODEL", "qwen-test")
        s = Settings.from_env()
        assert s.qwen_api_key == "test-key-123"
        assert s.qwen_base_url == "https://example.invalid/v1"
        assert s.llm_model == "qwen-test"

    def test_tavily_key_optional(self, mock_dotenv, monkeypatch):
        monkeypatch.setenv("QWEN_API_KEY", "test-key")
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        s = Settings.from_env()
        assert s.tavily_api_key == ""
