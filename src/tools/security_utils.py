"""
Security utilities for input validation and path sanitization.
Provides defense against injection attacks and path traversal vulnerabilities.
"""
import re
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse


def sanitize_path(file_path: Union[str, Path], base_path: Optional[Path] = None) -> Optional[Path]:
    """Sanitize and validate a file path to prevent directory traversal attacks.

    Args:
        file_path: Path to sanitize (can be string or Path)
        base_path: Base directory to resolve path against (prevents traversal)

    Returns:
        Sanitized Path object if valid, None if invalid or traversal detected

    Raises:
        ValueError: If path contains dangerous patterns
    """
    if not file_path:
        return None

    # Convert to Path and normalize (resolves mixed separators on Windows)
    path = Path(file_path) if isinstance(file_path, str) else file_path

    # Resolve to absolute path if base_path provided
    if base_path:
        try:
            resolved = (base_path / path).resolve()
            if not str(resolved).startswith(str(base_path.resolve())):
                raise ValueError(f"Path traversal detected: {file_path}")
            return resolved
        except (ValueError, OSError):
            return None

    # Basic sanitization: check the POSIX representation for dangerous patterns
    # Use as_posix() so Windows backslash paths don't false-positive on regex
    path_posix = path.as_posix()

    dangerous_patterns = [
        r'(?:^|/)\.\.(?:/|$)',   # Parent directory traversal (../ or /../)
        r'[<>"|?*]',            # Forbidden characters (exclude : for Windows drive letters)
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, path_posix):
            raise ValueError(f"Invalid path pattern detected: {file_path}")

    # Resolve to absolute to normalize the path
    return path.resolve()


def validate_repo_url(url: str) -> bool:
    """Validate repository URL format and prevent injection attacks.

    Args:
        url: Repository URL to validate

    Returns:
        True if URL is valid and safe, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    if not (url.startswith("http://") or
            url.startswith("https://") or
            url.startswith("git@")):
        return False

    if url.startswith("http"):
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc or len(parsed.netloc) > 255:
                return False
            if any(char in parsed.path for char in ['<', '>', '"', "'", '`', '|', ';', '&', '$']):
                return False
        except Exception:
            return False

    elif url.startswith("git@"):
        if ':' not in url[4:]:
            return False
        if any(char in url for char in ['<', '>', '"', "'", '`', '|', ';', '&', '$', '(', ')']):
            return False

    if len(url) > 2048:
        return False

    return True


def validate_pdf_path(pdf_path: Union[str, Path]) -> bool:
    """Validate PDF file path and ensure it's safe to open.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if path is valid and safe, False otherwise
    """
    if not pdf_path:
        return False

    path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path

    # Resolve relative paths to absolute BEFORE checking is_file()
    # This is critical — relative paths fail is_file() if CWD != project root
    try:
        path = path.resolve()
    except (OSError, ValueError):
        return False

    # Must be a file (not directory)
    if not path.is_file():
        return False

    # Must have .pdf extension
    if path.suffix.lower() != '.pdf':
        return False

    # Check file size (prevent DoS with huge files, limit 100MB)
    try:
        file_size = path.stat().st_size
        if file_size > 100 * 1024 * 1024:
            return False
    except OSError:
        return False

    # Path sanitization check
    try:
        sanitize_path(path)
    except ValueError:
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent injection and filesystem issues.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "unnamed"

    # Remove path components
    filename = Path(filename).name

    # Remove dangerous characters (Windows + Unix)
    dangerous_chars = '<>:"/\\|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing dots and spaces (Windows issue)
    filename = filename.strip('. ')

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')

    return filename or "unnamed"