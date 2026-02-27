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
    """Search for keywords in document chunks with fuzzy variant matching.

    Instead of exact phrase matching, each rubric keyword maps to a set of
    synonyms and alternate phrasings. This catches cases like:
    - "fan-out/fan-in" matching "Fan-In/Fan-Out"
    - "dialectical evaluation" matching "Dialectical Synthesis"
    - "operator.ior" matching "State Synchronization"

    Args:
        chunks: List of document chunks
        keywords: List of keywords to search for

    Returns:
        Dictionary with keyword matches and context
    """
    # Map each rubric keyword to variant phrases that indicate the same concept
    keyword_variants = {
        "Dialectical Synthesis": [
            "dialectical synthesis", "dialectical", "dialectic",
            "thesis-antithesis", "adversarial", "prosecutor.*defense",
            "multiple perspectives", "opposing perspectives",
            "judicial evaluation", "courtroom pattern",
            "digital courtroom", "dialectical reasoning",
        ],
        "Fan-In / Fan-Out": [
            "fan-in", "fan-out", "fan in", "fan out",
            "parallel fan", "fan-in/fan-out", "fan-out/fan-in",
            "parallel execution", "parallel edge", "parallel write",
            "concurrent", "superstep",
        ],
        "Fan-In/Fan-Out": [
            "fan-in", "fan-out", "fan in", "fan out",
            "fan-in/fan-out", "fan-out/fan-in",
            "parallel fan", "parallel execution",
        ],
        "Metacognition": [
            "metacognition", "metacognitive", "self-referential",
            "auditing itself", "audit.*audit", "self-aware",
            "introspection", "reflection on process",
        ],
        "State Synchronization": [
            "state synchronization", "state sync",
            "operator.ior", "operator.add", "reducer",
            "annotated reducer", "parallel.*merge",
            "parallel.*write", "state mutation",
            "merge evidence", "concatenate opinion",
        ],
    }

    matches = {}
    for keyword in keywords:
        matches[keyword] = []

        # Get variants for this keyword, or fall back to exact match
        variants = keyword_variants.get(keyword, [keyword.lower()])

        for chunk in chunks:
            content = chunk["content"] if isinstance(chunk, dict) else str(chunk)
            content_lower = content.lower()

            for variant in variants:
                # Support simple regex patterns (e.g. "prosecutor.*defense")
                try:
                    import re as _re
                    if _re.search(variant, content_lower):
                        idx = content_lower.find(variant.split(".*")[0])  # Find first part
                        if idx == -1:
                            idx = 0
                        start = max(0, idx - 200)
                        end = min(len(content), idx + len(variant) + 200)
                        context = content[start:end]

                        # Avoid duplicate matches for the same chunk
                        already_matched = any(
                            m["chunk_id"] == chunk.get("id", -1) for m in matches[keyword]
                        )
                        if not already_matched:
                            matches[keyword].append({
                                "chunk_id": chunk.get("id", 0),
                                "matched_variant": variant,
                                "context": context[:300],
                                "has_substance": _check_substance(context, keyword),
                            })
                        break  # One match per chunk per keyword is enough
                except Exception:
                    # Fallback to simple substring
                    if variant in content_lower:
                        idx = content_lower.find(variant)
                        start = max(0, idx - 200)
                        end = min(len(content), idx + len(variant) + 200)
                        context = content[start:end]
                        matches[keyword].append({
                            "chunk_id": chunk.get("id", 0),
                            "matched_variant": variant,
                            "context": context[:300],
                            "has_substance": _check_substance(context, keyword),
                        })
                        break

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


def ingest_report(report_path: Path) -> Dict:
    """Generic ingestion for a report that may be .pdf or .md.

    For now:
      - .pdf → use ingest_pdf()
      - .md  → read text and chunk using the same _chunk_text()
      - .doc/.docx → return an error (unsupported placeholder)
    """
    suffix = report_path.suffix.lower()

    # Prefer PDF via the existing ingest_pdf pipeline
    if suffix == ".pdf":
        return ingest_pdf(report_path)

    # Lightweight markdown ingestion
    if suffix == ".md":
        if not report_path.exists():
            return {
                "success": False,
                "error": f"Markdown report not found: {report_path}",
            }
        text = report_path.read_text(encoding="utf-8", errors="ignore")
        chunks = _chunk_text(text)
        return {
            "success": True,
            "chunks": chunks,
            "total_chunks": len(chunks),
            "method": "markdown",
        }

    # Placeholder for future DOC/DOCX support
    if suffix in (".doc", ".docx"):
        return {
            "success": False,
            "error": (
                f"Unsupported report format '{suffix}'. "
                "Install a DOC parser and extend ingest_report() to handle it."
            ),
        }

    return {
        "success": False,
        "error": f"Unsupported report format '{suffix}'.",
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
    """Extract images from a PDF document.

    Tries pymupdf first (better image extraction), falls back to pypdf.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of extracted images with metadata
    """
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


def extract_diagrams_from_report(report_path: Path) -> List[Dict]:
    """Extract diagram-like artifacts from a report.

    For now:
      - If report is a PDF  → use extract_images_from_pdf()
      - If report is a .md → treat mermaid code blocks as diagrams
      - Otherwise          → return empty list
    """
    suffix = report_path.suffix.lower()

    # 1) Real images from a PDF
    if suffix == ".pdf":
        return extract_images_from_pdf(report_path)

    # 2) Mermaid diagrams inside markdown
    if suffix == ".md":
        if not report_path.exists():
            return []

        text = report_path.read_text(encoding="utf-8", errors="ignore")
        diagrams: List[Dict] = []

        # 2a) Match fenced code blocks that look like mermaid diagrams.
        # Supports:
        # ```mermaid
        # graph TD
        #   ...
        # ```
        mermaid_pattern = re.compile(
            r"```(?:mermaid)?\s+([\s\S]*?)```",
            flags=re.IGNORECASE,
        )

        for idx, match in enumerate(mermaid_pattern.finditer(text), start=1):
            block = match.group(1).strip()
            block_lower = block.lower()
            if block_lower.startswith("graph") or "graph td" in block_lower:
                diagrams.append(
                    {
                        "index": idx,
                        "format": "mermaid",
                        "language": "mermaid",
                        "snippet": block[:400],
                    }
                )

        # 2b) Fallback: detect bare mermaid blocks without fences,
        # e.g. lines starting with "graph TD" as in many markdown docs.
        if not diagrams:
            lines = text.splitlines()
            current_block: List[str] = []
            capturing = False
            idx = 0

            for line in lines:
                stripped = line.strip()
                lower = stripped.lower()

                if not capturing:
                    if lower.startswith("graph ") or "graph td" in lower:
                        # Start a new diagram block
                        capturing = True
                        current_block = [line]
                        idx += 1
                else:
                    if not stripped:
                        # Blank line → end of diagram block
                        block = "\n".join(current_block).strip()
                        if block:
                            diagrams.append(
                                {
                                    "index": idx,
                                    "format": "mermaid",
                                    "language": "mermaid",
                                    "snippet": block[:400],
                                }
                            )
                        capturing = False
                        current_block = []
                    else:
                        current_block.append(line)

            # Flush last block if file ended without blank line
            if capturing and current_block:
                block = "\n".join(current_block).strip()
                diagrams.append(
                    {
                        "index": idx or 1,
                        "format": "mermaid",
                        "language": "mermaid",
                        "snippet": block[:400],
                    }
                )

        return diagrams

    # 3) Unsupported formats (doc/docx etc.) — no diagrams extracted yet
    return []