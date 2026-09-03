"""PDF text extraction — implements PRD FR-1.4 (extraction) and FR-1.5
(scanned/image-PDF detection)."""

from io import BytesIO

from pypdf import PdfReader


class PDFExtractionError(Exception):
    """Base error for anything that goes wrong while reading a PDF."""


class ScannedPDFError(PDFExtractionError):
    """Raised when extracted text is below the minimum threshold — most
    likely a scanned/image-only PDF with no real text layer (FR-1.5)."""


def extract_text(file_bytes: bytes, min_chars: int) -> str:
    """Extracts and concatenates text from every page of a PDF.

    Raises:
        PDFExtractionError: if the file can't be parsed as a PDF at all.
        ScannedPDFError: if extracted text is shorter than `min_chars`,
            signalling this is likely a scanned/image-based PDF (FR-1.5).
    """
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:  # pypdf raises several different exception types
        raise PDFExtractionError(f"Could not read PDF: {exc}") from exc

    pages_text = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages_text).strip()

    if len(full_text) < min_chars:
        raise ScannedPDFError(
            "No extractable text found — this PDF may be scanned/image-based."
        )

    return full_text
