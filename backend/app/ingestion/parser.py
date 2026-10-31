import logging
from pathlib import Path

import fitz  # pymupdf

logger = logging.getLogger(__name__)

MIME_MAP = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def get_mime_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return MIME_MAP.get(ext, "application/octet-stream")


def parse_file(file_path: str) -> tuple[bytes, str]:
    """
    Reads a file and returns (content_bytes, mime_type).
    For PDFs, converts to images if needed; for images, reads raw bytes.
    For multi-page PDFs, renders the first page to an image.
    """
    path = Path(file_path)
    mime_type = get_mime_type(file_path)

    if mime_type == "application/pdf":
        # Read raw PDF bytes — Claude and GPT-4o can handle PDFs directly
        content = path.read_bytes()
        logger.info(f"Parsed PDF: {path.name} ({len(content)} bytes)")
        return content, mime_type
    else:
        content = path.read_bytes()
        logger.info(f"Parsed image: {path.name} ({len(content)} bytes)")
        return content, mime_type


def pdf_to_images(file_path: str) -> list[tuple[bytes, str]]:
    """Convert each page of a PDF to a PNG image. Used for providers that don't support PDF input."""
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        pages.append((pix.tobytes("png"), "image/png"))
    doc.close()
    return pages
