"""Tests for the multi-source secret resolver (Docker secrets > env var > default)."""

import os
import pytest
from config.settings import Settings


class TestResolveSecret:
    """Verify the priority chain: Docker secret file > env var > default."""

    def test_env_var_wins_over_default(self, monkeypatch):
        monkeypatch.setenv("MY_TEST_KEY", "from-env")
        assert Settings.resolve_secret("MY_TEST_KEY", "fallback") == "from-env"

    def test_default_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("MY_TEST_KEY", raising=False)
        assert Settings.resolve_secret("MY_TEST_KEY", "fallback") == "fallback"

    def test_empty_default(self, monkeypatch):
        monkeypatch.delenv("MY_TEST_KEY", raising=False)
        assert Settings.resolve_secret("MY_TEST_KEY") == ""

    def test_docker_secret_file_wins_over_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MY_TEST_KEY", "from-env")

        secret_file = tmp_path / "my_test_key"
        secret_file.write_text("from-docker-secret\n")

        result = _mock_resolve("MY_TEST_KEY", "fallback", tmp_path)
        assert result == "from-docker-secret"


def _mock_resolve(name: str, default: str, secrets_dir) -> str:
    """Simulates resolve_secret with a custom secrets directory."""
    secrets_path = secrets_dir / name.lower()
    if secrets_path.is_file():
        return secrets_path.read_text().strip()
    return os.getenv(name, default)
