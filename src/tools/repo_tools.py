"""
Repository investigation tools.
Wrapper module that combines git_tools and ast_tools for compatibility.
"""
from src.tools.ast_tools import (
    check_parallel_edges,
    check_pydantic_models,
    check_sandboxing,
    check_security,
    check_stategraph,
    check_structured_output,
)
from src.tools.git_tools import extract_git_history, safe_clone

# Re-export all functions for compatibility
__all__ = [
    "safe_clone",
    "extract_git_history",
    "check_stategraph",
    "check_pydantic_models",
    "check_parallel_edges",
    "check_sandboxing",
    "check_structured_output",
    "check_security",
]
