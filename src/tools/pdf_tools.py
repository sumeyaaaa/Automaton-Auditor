"""
PDF document analysis tools.
Implements RAG-lite approach for chunked document querying.

PDF parsing priority:
  1. pymupdf (fitz) — fastest, best image extraction
  2. pdfplumber — good table/layout parsing
  3. pypdf — lightweight fallback
  4. docling — heavyweight, ML-based (slow but accurate)

Install at least one:
  pip install pymupdf          # recommended
  pip install pdfplumber       # alternative
  pip install pypdf            # lightweight fallback
"""
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from src.exceptions import PDFNotFoundError, PDFParseError
from src.tools.security_utils import validate_pdf_path, sanitize_path

logger = logging.getLogger(__name__)

# ── Optional PDF library imports ──────────────────────────
# Try multiple libraries in priority order.

try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False

# Log which libraries are available at import time
_available = [
    name for name, flag in [
        ("pymupdf", HAS_PYMUPDF),
        ("pdfplumber", HAS_PDFPLUMBER),
        ("pypdf", HAS_PYPDF),
        ("docling", HAS_DOCLING),
    ] if flag
]
if _available:
    logger.info("PDF libraries available: %s", ", ".join(_available))
else:
    logger.warning(
        "No PDF parsing library found. Install one: "
        "pip install pymupdf  OR  pip install pdfplumber  OR  pip install pypdf"
    )


def ingest_pdf(pdf_path: Path) -> Dict:
    """Ingest and chunk PDF document for analysis.

    Tries parsers in priority order: pymupdf → pdfplumber → pypdf → docling.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with document chunks and metadata

    Raises:
        PDFNotFoundError: If the PDF file doesn't exist
        PDFParseError: If no parser can handle the file
    """
    # Security: Validate PDF path before processing
    if not validate_pdf_path(pdf_path):
        raise PDFNotFoundError(
            f"Invalid or unsafe PDF path: {pdf_path}. "
            "Path must be a valid .pdf file under 100MB."
        )
    
    # Sanitize path to prevent traversal
    try:
        sanitized_path = sanitize_path(pdf_path)
        if not sanitized_path:
            raise PDFNotFoundError(f"Path sanitization failed: {pdf_path}")
        pdf_path = sanitized_path
    except ValueError as e:
        raise PDFNotFoundError(f"Path validation failed: {e}")
    
    if not pdf_path.exists():
        raise PDFNotFoundError(str(pdf_path))

    errors: list[str] = []

    # ── 1. pymupdf (fitz) — fastest, best quality ──
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(str(pdf_path))
            text_content = ""
            for page in doc:
                text_content += page.get_text() + "\n"
            doc.close()

            chunks = _chunk_text(text_content)
            return {
                "success": True,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "method": "pymupdf",
            }
        except Exception as e:
            errors.append(f"pymupdf: {e}")

    # ── 2. pdfplumber — good for tables/layout ──
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                text_content = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"

            chunks = _chunk_text(text_content)
            return {
                "success": True,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "method": "pdfplumber",
            }
        except Exception as e:
            errors.append(f"pdfplumber: {e}")

    # ── 3. pypdf — lightweight fallback ──
    if HAS_PYPDF:
        try:
            reader = PdfReader(str(pdf_path))
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n"

            chunks = _chunk_text(text_content)
            return {
                "success": True,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "method": "pypdf",
            }
        except Exception as e:
            errors.append(f"pypdf: {e}")

    # ── 4. docling — heavyweight ML parser (slow) ──
    if HAS_DOCLING:
        try:
            pipeline_options = PdfPipelineOptions()
            converter = DocumentConverter(
                format=InputFormat.PDF, pipeline_options=pipeline_options
            )
            doc = converter.convert(str(pdf_path))
            text_content = doc.export_to_markdown()

            chunks = _chunk_text(text_content)
            return {
                "success": True,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "method": "docling",
            }
        except Exception as e:
            errors.append(f"docling: {e}")

    # ── All parsers failed or none installed ──
    if errors:
        error_msg = "All PDF parsers failed: " + "; ".join(errors)
    else:
        error_msg = (
            "No PDF parsing library installed. "
            "Install one: pip install pymupdf  OR  pip install pdfplumber  OR  pip install pypdf"
        )
    raise PDFParseError(str(pdf_path), error_msg)


def _chunk_text(text: str, chunk_size: int = 1000) -> List[Dict]:
    """Split text into chunks for RAG-lite querying.

    Args:
        text: Full text content
        chunk_size: Target chunk size in characters

    Returns:
        List of chunk dictionaries with content and metadata
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    chunk_id = 0

    for para in paragraphs:
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append({
                    "id": chunk_id,
                    "content": current_chunk.strip(),
                    "length": len(current_chunk),
                })
                chunk_id += 1
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append({
            "id": chunk_id,
            "content": current_chunk.strip(),
            "length": len(current_chunk),
        })

    return chunks


def search_keywords(chunks: List[Dict], keywords: List[str]) -> Dict:
    """Search for keywords in document chunks.

    Args:
        chunks: List of document chunks
        keywords: List of keywords to search for

    Returns:
        Dictionary with keyword matches and context
    """
    matches = {}
    for keyword in keywords:
        matches[keyword] = []
        keyword_lower = keyword.lower()

        for chunk in chunks:
            content_lower = chunk["content"].lower()
            if keyword_lower in content_lower:
                idx = content_lower.find(keyword_lower)
                start = max(0, idx - 200)
                end = min(len(chunk["content"]), idx + len(keyword) + 200)
                context = chunk["content"][start:end]

                matches[keyword].append({
                    "chunk_id": chunk["id"],
                    "context": context,
                    "has_substance": _check_substance(context, keyword),
                })

    return {
        "keywords": keywords,
        "matches": matches,
        "summary": _summarize_matches(matches),
    }


def _check_substance(context: str, keyword: str) -> bool:
    """Check if keyword appears with substantive explanation.

    Args:
        context: Text context around keyword
        keyword: The keyword being checked

    Returns:
        True if keyword appears with explanation, False if just mentioned
    """
    explanation_patterns = [
        r"because",
        r"by",
        r"through",
        r"using",
        r"implements",
        r"executes",
        r"achieves",
    ]
    context_lower = context.lower()
    return any(pattern in context_lower for pattern in explanation_patterns)


def _summarize_matches(matches: Dict) -> Dict:
    """Summarize keyword match results.

    Args:
        matches: Dictionary of keyword matches

    Returns:
        Summary statistics
    """
    total_matches = sum(len(m) for m in matches.values())
    substantive_matches = sum(
        sum(1 for m in matches[k] if m["has_substance"])
        for k in matches
    )

    return {
        "total_occurrences": total_matches,
        "substantive_occurrences": substantive_matches,
        "keyword_dropping": total_matches - substantive_matches,
    }


def extract_file_path_claims(chunks: List[Dict]) -> List[str]:
    """Extract file paths mentioned in the document.

    Args:
        chunks: List of document chunks

    Returns:
        List of extracted file paths
    """
    file_paths = []
    path_pattern = r"(?:src/|\./)?[\w/]+\.(?:py|md|toml|json|yaml|yml)"

    for chunk in chunks:
        matches = re.findall(path_pattern, chunk["content"])
        file_paths.extend(matches)

    unique_paths = list(set(file_paths))
    return unique_paths


def extract_images_from_pdf(pdf_path: Path) -> List[Dict]:
    """Extract images from PDF document.

    Tries pymupdf first (better image extraction), falls back to pypdf.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of extracted images with metadata
    """
    # Security: Validate PDF path before processing
    if not validate_pdf_path(pdf_path):
        logger.warning(f"Invalid or unsafe PDF path: {pdf_path}")
        return []
    
    # Sanitize path to prevent traversal
    try:
        sanitized_path = sanitize_path(pdf_path)
        if not sanitized_path:
            return []
        pdf_path = sanitized_path
    except ValueError:
        logger.warning(f"Path sanitization failed: {pdf_path}")
        return []
    
    if not pdf_path.exists():
        return []

    # ── pymupdf: best image extraction ──
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(str(pdf_path))
            images = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    images.append({
                        "page": page_num + 1,
                        "xref": xref,
                        "format": base_image.get("ext", "unknown"),
                        "width": base_image.get("width", 0),
                        "height": base_image.get("height", 0),
                        "size_bytes": len(base_image.get("image", b"")),
                    })
            doc.close()
            return images
        except Exception as e:
            logger.warning("pymupdf image extraction failed: %s", e)

    # ── pypdf fallback ──
    if HAS_PYPDF:
        try:
            reader = PdfReader(str(pdf_path))
            images = []

            for page_num, page in enumerate(reader.pages):
                resources = page.get("/Resources")
                if resources is None:
                    continue
                x_objects = resources.get("/XObject")
                if x_objects is None:
                    continue

                x_object = x_objects.get_object()
                for obj in x_object:
                    if x_object[obj].get("/Subtype") == "/Image":
                        images.append({
                            "page": page_num + 1,
                            "object_id": obj,
                            "format": "unknown",
                        })

            return images
        except Exception as e:
            logger.warning("pypdf image extraction failed: %s", e)
            return []

    return []