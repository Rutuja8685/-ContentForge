"""Parser service – placeholder; fully implemented in Phase 4."""


def parse_text(text: str) -> str:
    """Return clean text from pasted input."""
    return text.strip()


def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes. Implemented in Phase 4."""
    raise NotImplementedError("PDF parsing implemented in Phase 4")


def parse_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes. Implemented in Phase 4."""
    raise NotImplementedError("DOCX parsing implemented in Phase 4")


def parse_url(url: str) -> str:
    """Fetch and extract text from a URL. Implemented in Phase 4."""
    raise NotImplementedError("URL parsing implemented in Phase 4")


def parse_image(file_bytes: bytes) -> str:
    """Describe image via Gemini multimodal. Implemented in Phase 4."""
    raise NotImplementedError("Image parsing implemented in Phase 4")
