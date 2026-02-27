"""
Git tools for safe repository operations.
All operations use sandboxed temporary directories for security.
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

import git
from git import Repo

from src.exceptions import GitOperationError, InvalidRepositoryError, RepositoryCloneError
from src.tools.security_utils import validate_repo_url, sanitize_path


def safe_clone(repo_url: str, timeout: int = 60, shallow: bool = False) -> tuple[Path, str]:
    """Clone repository into a sandboxed temporary directory.
    
    Args:
        repo_url: GitHub repository URL
        timeout: Timeout in seconds for git operations
        shallow: If True, use shallow clone (depth=1) for speed. 
                 If False, clone full history for forensic analysis.
        
    Returns:
        Tuple of (repo_path, commit_hash)
        
    Raises:
        InvalidRepositoryError: If repo_url is invalid
        RepositoryCloneError: If clone fails
    """
    if not repo_url or not isinstance(repo_url, str):
        raise InvalidRepositoryError(repo_url, "Repository URL is empty or not a string")

    # Validate and sanitize URL
    if not validate_repo_url(repo_url):
        raise InvalidRepositoryError(
            repo_url, 
            "Repository URL is invalid or contains dangerous characters. "
            "Must be a valid HTTP/HTTPS URL or git@ URL."
        )

    # Create temporary directory for sandboxing
    # Note: Using mkdtemp instead of TemporaryDirectory context manager
    # because the repo_path needs to persist after this function returns
    # (it's used by detectives for analysis). Cleanup is handled by the OS
    # or by explicit cleanup in the graph execution if needed.
    temp_dir = tempfile.mkdtemp(prefix="auditor_repo_")
    repo_path = Path(temp_dir) / "repo"

    try:
        # Clone with error handling
        # For forensic analysis, we need full history to count commits correctly
        # Only use shallow clone if explicitly requested (for speed, but loses history)
        if shallow:
            repo = Repo.clone_from(repo_url, str(repo_path), depth=1)
        else:
            # Full clone to get complete commit history for forensic analysis
            repo = Repo.clone_from(repo_url, str(repo_path))
        
        # Get current commit hash
        commit_hash = repo.head.commit.hexsha[:8]
        
        return repo_path, commit_hash
    except git.exc.GitCommandError as e:
        error_msg = str(e)
        if "Authentication failed" in error_msg or "Permission denied" in error_msg:
            raise RepositoryCloneError(repo_url, "Authentication failed. Check credentials or repository access.")
        elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            raise InvalidRepositoryError(repo_url, "Repository not found or does not exist")
        else:
            raise RepositoryCloneError(repo_url, error_msg)
    except Exception as e:
        raise RepositoryCloneError(repo_url, f"Unexpected error: {str(e)}")


def extract_git_history(repo_path: Path) -> Dict:
    """Extract git commit history for forensic analysis.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with commit history data
    """
    try:
        # Validate and sanitize repo_path
        sanitized_path = sanitize_path(repo_path)
        if not sanitized_path or not sanitized_path.exists():
            return {
                "error": "Invalid repository path",
                "total_commits": 0,
                "commits": [],
            }
        
        repo = Repo(str(sanitized_path))
        
        # Use subprocess for git log (as per Architecture.MD spec)
        # Security: shell=False prevents shell injection
        result = subprocess.run(
            ["git", "log", "--oneline", "--reverse"],
            cwd=str(sanitized_path),
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,  # Security: no shell
        )
        
        if result.returncode != 0:
            raise GitOperationError("git log", result.stderr or "Unknown error")
        
        commits = list(repo.iter_commits())
        commit_data = []
        
        for commit in reversed(commits):  # Reverse to get chronological order
            commit_data.append({
                "hash": commit.hexsha[:8],
                "message": commit.message.strip(),
                "timestamp": commit.committed_datetime.isoformat(),
                "author": commit.author.name,
            })
        
        return {
            "total_commits": len(commits),
            "commits": commit_data,
            "is_atomic": len(commits) > 3,
            "has_progression": _analyze_progression(commit_data),
            "log_output": result.stdout,
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_commits": 0,
            "commits": [],
        }


def _analyze_progression(commits: list[Dict]) -> bool:
    """Analyze if commit history shows progression.
    
    Args:
        commits: List of commit dictionaries
        
    Returns:
        True if progression pattern detected
    """
    if len(commits) < 3:
        return False
    
    # Check for progression keywords
    progression_keywords = [
        "setup", "init", "tool", "graph", "node", "state", "judge", "detective"
    ]
    messages = " ".join([c["message"].lower() for c in commits])
    return any(keyword in messages for keyword in progression_keywords)

