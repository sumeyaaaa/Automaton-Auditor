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


def safe_clone(repo_url: str, timeout: int = 60) -> tuple[Path, str]:
    """Clone repository into a sandboxed temporary directory.
    
    Args:
        repo_url: GitHub repository URL
        timeout: Timeout in seconds for git operations
        
    Returns:
        Tuple of (repo_path, commit_hash)
        
    Raises:
        ValueError: If repo_url is invalid or clone fails
    """
    if not repo_url or not isinstance(repo_url, str):
        raise ValueError("Invalid repository URL")

    # Sanitize URL (basic check)
    if not (repo_url.startswith("http") or repo_url.startswith("git@")):
        raise ValueError(f"Invalid repository URL format: {repo_url}")

    # Create temporary directory for sandboxing
    temp_dir = tempfile.mkdtemp(prefix="auditor_repo_")
    repo_path = Path(temp_dir) / "repo"

    try:
        # Clone with error handling
        repo = Repo.clone_from(
            repo_url,
            str(repo_path),
            depth=1,  # Shallow clone for speed
        )
        
        # Get current commit hash
        commit_hash = repo.head.commit.hexsha[:8]
        
        return repo_path, commit_hash
    except git.exc.GitCommandError as e:
        raise ValueError(f"Failed to clone repository: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error during clone: {str(e)}")


def extract_git_history(repo_path: Path) -> Dict:
    """Extract git commit history for forensic analysis.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with commit history data
    """
    try:
        repo = Repo(str(repo_path))
        
        # Use subprocess for git log (as per Architecture.MD spec)
        result = subprocess.run(
            ["git", "log", "--oneline", "--reverse"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,  # Security: no shell
        )
        
        if result.returncode != 0:
            return {
                "error": f"git log failed: {result.stderr}",
                "total_commits": 0,
                "commits": [],
            }
        
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

