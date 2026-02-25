"""
Document analysis tools.
Wrapper module for PDF parsing and analysis.
"""
from src.tools.pdf_tools import (
    extract_file_path_claims,
    extract_images_from_pdf,
    ingest_pdf,
    search_keywords,
)

# Re-export all functions for compatibility
__all__ = [
    "ingest_pdf",
    "search_keywords",
    "extract_file_path_claims",
    "extract_images_from_pdf",
]
