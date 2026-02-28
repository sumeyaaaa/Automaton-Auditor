"""Pytest configuration and fixtures."""
import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_rubric():
    """Load sample rubric for testing."""
    rubric_path = Path("rubric.json")
    if rubric_path.exists():
        with open(rubric_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "dimensions": [
            {
                "id": "git_forensic_analysis",
                "name": "Git Forensic Analysis",
                "target_artifact": "github_repo",
                "forensic_instruction": "Analyze git commit history",
            }
        ],
        "synthesis_rules": {},
    }


@pytest.fixture
def sample_state():
    """Create sample AgentState for testing."""
    from src.state import AgentState

    return {
        "repo_url": "https://github.com/test/repo.git",
        "pdf_path": "test.pdf",
        "rubric_dimensions": [],
        "evidences": {},
        "opinions": [],
        "final_report": None,
        "synthesis_rules": {},
        "git_commit_hash": "",
        "model_metadata": {},
    }


