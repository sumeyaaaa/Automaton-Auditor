"""Unit tests for ast_tools."""
import tempfile
from pathlib import Path

import pytest

from src.tools.ast_tools import (
    check_pydantic_models,
    check_sandboxing,
    check_security,
    check_stategraph,
)


class TestASTTools:
    """Test AST analysis tools."""

    def test_check_stategraph_nonexistent_path(self):
        """Test check_stategraph with non-existent path."""
        result = check_stategraph(Path("/nonexistent/path"))
        assert result.get("found", False) is False

    def test_check_pydantic_models_nonexistent_path(self):
        """Test check_pydantic_models with non-existent path."""
        result = check_pydantic_models(Path("/nonexistent/path"))
        assert result.get("found", False) is False

    def test_check_sandboxing_nonexistent_path(self):
        """Test check_sandboxing with non-existent path."""
        result = check_sandboxing(Path("/nonexistent/path"))
        assert result.get("found", False) is False

    def test_check_security_nonexistent_path(self):
        """Test check_security with non-existent path."""
        result = check_security(Path("/nonexistent/path"))
        assert result.get("found", False) is False


