"""
PDF document analysis tools.
Implements RAG-lite approach for chunked document querying.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def ingest_pdf(pdf_path: Path) -> Dict:
    """Ingest and chunk PDF document for analysis.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary with document chunks and metadata
    """
    if not pdf_path.exists():
        return {
            "success": False,
            "error": f"PDF file not found: {pdf_path}",
        }

    try:
        # Try Docling first (better parsing)
        if DOCLING_AVAILABLE:
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
                # Fallback to pypdf if docling fails
                pass
        
        # Fallback to pypdf
        if PYPDF_AVAILABLE:
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
        else:
            return {
                "success": False,
                "error": "No PDF parsing library available",
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def _chunk_text(text: str, chunk_size: int = 1000) -> List[Dict]:
    """Split text into chunks for RAG-lite querying.
    
    Args:
        text: Full text content
        chunk_size: Target chunk size in characters
        
    Returns:
        List of chunk dictionaries with content and metadata
    """
    # Simple chunking by paragraphs first
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

    # Add final chunk
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
                # Extract context around keyword
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
    # Simple heuristic: check for explanation patterns
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
    return any(
        pattern in context_lower
        for pattern in explanation_patterns
    )


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
    # Pattern for common file paths
    path_pattern = r"(?:src/|\./)?[\w/]+\.(?:py|md|toml|json|yaml|yml)"

    for chunk in chunks:
        matches = re.findall(path_pattern, chunk["content"])
        file_paths.extend(matches)

    # Deduplicate and clean
    unique_paths = list(set(file_paths))
    return unique_paths


def extract_images_from_pdf(pdf_path: Path) -> List[Dict]:
    """Extract images from PDF document.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of extracted images with metadata
    """
    if not PYPDF_AVAILABLE:
        return []

    try:
        reader = PdfReader(str(pdf_path))
        images = []
        
        for page_num, page in enumerate(reader.pages):
            if "/XObject" in page.get("/Resources", {}):
                x_object = page["/Resources"]["/XObject"].get_object()
                
                for obj in x_object:
                    if x_object[obj].get("/Subtype") == "/Image":
                        images.append({
                            "page": page_num + 1,
                            "object_id": obj,
                        })
        
        return images
    except Exception as e:
        return [{"error": str(e)}]

