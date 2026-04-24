"""Unit tests for RBAC metadata filter logic (no API calls)."""

import pytest
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
from tools.rag_tool import RAGTool
from config.settings import Settings


def _make_settings() -> Settings:
    return Settings(qwen_api_key="test-key")


class TestRBACFilterLogic:

    def test_admin_gets_no_filter(self):
        result = RAGTool.build_filters("admin")
        assert result is None, "Admin should have unrestricted access (no filter)"

    def test_intern_gets_public_only_filter(self):
        result = RAGTool.build_filters("intern")
        assert isinstance(result, MetadataFilters)
        assert len(result.filters) == 1
        assert result.filters[0].key == "access_level"
        assert result.filters[0].value == "all"

    def test_unknown_role_gets_public_only_filter(self):
        """Any role that isn't 'admin' should be restricted."""
        result = RAGTool.build_filters("viewer")
        assert isinstance(result, MetadataFilters)
        assert result.filters[0].value == "all"

    def test_empty_role_gets_public_only_filter(self):
        result = RAGTool.build_filters("")
        assert isinstance(result, MetadataFilters)

    def test_case_sensitive_admin(self):
        """Role matching is case-sensitive — 'Admin' != 'admin'."""
        result = RAGTool.build_filters("Admin")
        assert isinstance(result, MetadataFilters), "Role should be case-sensitive"
