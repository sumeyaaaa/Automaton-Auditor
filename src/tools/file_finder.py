"""
File finding utilities for detective nodes.
Provides recursive and fuzzy search capabilities.
"""
import os
from pathlib import Path
from typing import List, Optional

from src.tools.security_utils import sanitize_path


def find_file_recursive(repo_path: Path, filename: str, max_depth: int = 3) -> Optional[Path]:
    """Recursively search for a file in the repository.
    
    Args:
        repo_path: Root of repository
        filename: File to find (e.g., "graph.py", "state.py")
        max_depth: Maximum directory depth to search
        
    Returns:
        Path to file if found, None otherwise
    """
    # Security: Sanitize inputs
    try:
        sanitized_repo = sanitize_path(repo_path)
        if not sanitized_repo or not sanitized_repo.exists():
            return None
        repo_path = sanitized_repo
    except ValueError:
        return None
    
    # Sanitize filename to prevent path traversal
    from src.tools.security_utils import sanitize_filename
    safe_filename = sanitize_filename(filename)
    
    # Common locations to check first (fast path)
    common_paths = [
        repo_path / "src" / safe_filename,
        repo_path / safe_filename,
        repo_path / "lib" / safe_filename,
        repo_path / "app" / safe_filename,
        repo_path / "core" / safe_filename,
    ]
    
    for path in common_paths:
        try:
            # Ensure path is still within repo_path (prevent traversal)
            if path.exists() and str(path.resolve()).startswith(str(repo_path.resolve())):
                return path
        except (OSError, ValueError):
            continue
    
    # Recursive search (limited depth for performance)
    for root, dirs, files in os.walk(repo_path):
        # Calculate depth relative to repo_path
        rel_path = Path(root).relative_to(repo_path)
        depth = len(rel_path.parts)
        
        if depth > max_depth:
            dirs[:] = []  # Don't descend further
            continue
        
        # Skip common directories that are unlikely to contain source files
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', 'dist', 'build')]
        
        if filename in files:
            return Path(root) / filename
    
    return None


def find_file_fuzzy(repo_path: Path, pattern: str, max_results: int = 5) -> List[Path]:
    """Fuzzy search for files matching a pattern.
    
    Useful when exact filename is unknown (e.g., "graph" might be "graph.py", "graph_builder.py", etc.)
    
    Args:
        repo_path: Root of repository
        pattern: Pattern to search for (case-insensitive)
        max_results: Maximum number of results to return
        
    Returns:
        List of matching file paths
    """
    matches = []
    pattern_lower = pattern.lower()
    
    for root, dirs, files in os.walk(repo_path):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', 'dist', 'build')]
        
        for file in files:
            if pattern_lower in file.lower() and file.endswith(('.py', '.js', '.ts', '.md')):
                matches.append(Path(root) / file)
                if len(matches) >= max_results:
                    return matches
    
    return matches


def get_repo_structure_sample(repo_path: Path, max_files: int = 20) -> List[str]:
    """Get a sample of repository file structure for LLM analysis.
    
    Args:
        repo_path: Root of repository
        max_files: Maximum number of files to return
        
    Returns:
        List of relative file paths
    """
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', 'dist', 'build')]
        
        for filename in filenames:
            if filename.endswith(('.py', '.js', '.ts', '.md', '.json')):
                rel_path = Path(root).relative_to(repo_path) / filename
                files.append(str(rel_path).replace('\\', '/'))
                if len(files) >= max_files:
                    return files
    
    return files


def find_interim_report_file(repo_path: Path) -> Optional[Path]:
    """Locate an interim report file inside a cloned repository.

    Looks under ``reports/`` for one of:
      - interim_report.md
      - interim_report.pdf
      - interim_report.doc
      - interim_report.docx

    Returns:
        Path to the first matching file, or None if not found.
    """
    candidates = [
        repo_path / "reports" / "interim_report.md",
        repo_path / "reports" / "interim_report.pdf",
        repo_path / "reports" / "interim_report.doc",
        repo_path / "reports" / "interim_report.docx",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


