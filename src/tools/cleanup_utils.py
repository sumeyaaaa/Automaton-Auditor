"""
Utilities for cleaning up temporary directories and resources.
Provides safe cleanup mechanisms for sandboxed operations.
"""
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union


def cleanup_temp_directory(temp_path: Union[Path, str]) -> bool:
    """Safely remove a temporary directory and all its contents.
    
    Args:
        temp_path: Path to the temporary directory to clean up
        
    Returns:
        True if cleanup succeeded, False otherwise
    """
    try:
        path = Path(temp_path) if isinstance(temp_path, str) else temp_path
        
        # Safety check: only clean up paths that look like temp directories
        if not path.exists():
            return True  # Already cleaned up
        
        path_str = str(path)
        # Only clean up paths in temp directories (security measure)
        if not any(
            temp_dir in path_str 
            for temp_dir in [tempfile.gettempdir(), "/tmp", "\\Temp"]
        ):
            return False  # Not a temp directory - don't clean up
        
        # Only clean up our own temp directories (prefix check)
        if "auditor_repo_" not in path_str:
            return False  # Not our temp directory - don't clean up
        
        shutil.rmtree(path, ignore_errors=True)
        return True
    except Exception:
        return False


def get_temp_dir_info(temp_path: Union[Path, str]) -> Optional[dict]:
    """Get information about a temporary directory.
    
    Args:
        temp_path: Path to the temporary directory
        
    Returns:
        Dictionary with directory info, or None if invalid
    """
    try:
        path = Path(temp_path) if isinstance(temp_path, str) else temp_path
        
        if not path.exists():
            return None
        
        stat = path.stat()
        return {
            "path": str(path),
            "exists": True,
            "size_bytes": sum(
                f.stat().st_size 
                for f in path.rglob("*") 
                if f.is_file()
            ) if path.is_dir() else 0,
            "file_count": len(list(path.rglob("*"))) if path.is_dir() else 0,
        }
    except Exception:
        return None

