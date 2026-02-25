"""Unit tests for git_tools."""
import tempfile
from pathlib import Path

import pytest

from src.tools.git_tools import extract_git_history, safe_clone


class TestSafeClone:
    """Test safe_clone function."""

    def test_safe_clone_invalid_url(self):
        """Test safe_clone with invalid URL."""
        with pytest.raises(ValueError):
            safe_clone("")

        with pytest.raises(ValueError):
            safe_clone("not-a-url")

    def test_safe_clone_nonexistent_repo(self):
        """Test safe_clone with non-existent repository."""
        with pytest.raises(ValueError):
            safe_clone("https://github.com/nonexistent/repo-that-does-not-exist-12345.git")


class TestExtractGitHistory:
    """Test extract_git_history function."""

    def test_extract_git_history_nonexistent_path(self):
        """Test extract_git_history with non-existent path."""
        result = extract_git_history(Path("/nonexistent/path"))
        assert "error" in result or result.get("total_commits", 0) == 0

