"""Verify all tools implement the BaseTool interface correctly."""

import pytest
from tools.base_tool import BaseTool
from tools.calculator_tool import CalculatorTool
from tools.rag_tool import RAGTool
from tools.web_search_tool import WebSearchTool
from config.settings import Settings


def _make_settings(**overrides) -> Settings:
    """Create a Settings instance with dummy API keys for interface testing."""
    defaults = {"qwen_api_key": "test-key", "tavily_api_key": "test-key"}
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
def all_tools():
    settings = _make_settings()
    return [
        CalculatorTool(),
        RAGTool(settings),
        WebSearchTool(settings),
    ]


class TestBaseToolContract:
    def test_all_are_subclasses(self, all_tools):
        for tool in all_tools:
            assert isinstance(tool, BaseTool), f"{type(tool).__name__} is not a BaseTool"

    def test_names_are_unique(self, all_tools):
        names = [t.name for t in all_tools]
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"

    def test_names_are_strings(self, all_tools):
        for tool in all_tools:
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

    def test_descriptions_are_strings(self, all_tools):
        for tool in all_tools:
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

    def test_execute_is_callable(self, all_tools):
        for tool in all_tools:
            assert callable(tool.execute)


class TestWebSearchGracefulDegradation:
    def test_missing_api_key_returns_message(self):
        settings = _make_settings(tavily_api_key="")
        tool = WebSearchTool(settings)
        result = tool.execute("test query")
        assert "TAVILY_API_KEY" in result
        assert "unavailable" in result.lower()
