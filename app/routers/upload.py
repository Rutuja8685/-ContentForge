"""Extraction endpoint for uploaded files, web pages, and images."""

import asyncio
import io
import logging
import zipfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.schemas.generate import ExtractResponse
from app.services import parser_service
from app.services.parser_service import Extraction
from app.services.security_service import (
    neutralize_source_delimiters,
    scan_for_injection,
)

logger = logging.getLogger(__name__)
router = APIRouter()
MAX_EXTRACTED_CHARS = 20_000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

EXTENSION_DETAILS = {
    ".pdf": ("pdf", {"application/pdf"}),
    ".docx": (
        "docx",
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    ),
    ".txt": ("text", {"text/plain"}),
    ".md": ("text", {"text/markdown", "text/plain", "text/x-markdown"}),
    ".png": ("image", {"image/png"}),
    ".jpg": ("image", {"image/jpeg"}),
    ".jpeg": ("image", {"image/jpeg"}),
    ".webp": ("image", {"image/webp"}),
}


@router.get("/ping")
async def upload_ping():
    """Health check for the upload router."""
    return {"router": "upload", "status": "ok"}


def _detect_content(file_bytes: bytes) -> tuple[str, str]:
    if file_bytes.startswith(b"%PDF-"):
        return "pdf", "application/pdf"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png"
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg"
    if (
        len(file_bytes) >= 12
        and file_bytes[:4] == b"RIFF"
        and file_bytes[8:12] == b"WEBP"
    ):
        return "image", "image/webp"
    if file_bytes.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                if "word/document.xml" in archive.namelist():
                    return (
                        "docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
        except zipfile.BadZipFile:
            pass
        raise ValueError("The uploaded ZIP-based file is not a valid DOCX document.")
    if b"\x00" not in file_bytes:
        try:
            file_bytes.decode("utf-8-sig")
            return "text", "text/plain"
        except UnicodeDecodeError:
            pass
    raise ValueError("The file content is not a supported PDF, DOCX, TXT, MD, or image.")


def _validate_uploaded_file(
    filename: str | None, declared_mime: str | None, file_bytes: bytes
) -> tuple[str, str]:
    extension = ""
    if filename:
        extension = "." + filename.rsplit(".", maxsplit=1)[-1].lower()
        if "." not in filename:
            extension = ""
    extension_details = EXTENSION_DETAILS.get(extension)
    if extension_details is None:
        raise HTTPException(
            status_code=415,
            detail="Supported file types are PDF, DOCX, TXT, MD, PNG, JPG, and WEBP.",
        )

    detected_type, detected_mime = _detect_content(file_bytes)
    expected_type, allowed_mimes = extension_details
    if detected_type != expected_type:
        raise HTTPException(
            status_code=415,
            detail="The file content does not match its filename extension.",
        )
    if declared_mime not in allowed_mimes and not (
        expected_type == "text" and declared_mime == "text/plain"
    ):
        raise HTTPException(
            status_code=415,
            detail="The uploaded file MIME type is not supported for its extension.",
        )
    if expected_type == "image":
        try:
            with Image.open(io.BytesIO(file_bytes)) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise HTTPException(
                status_code=415,
                detail="The uploaded image is invalid or unreadable.",
            ) from error
    return expected_type, detected_mime


def _trim_extraction(
    extraction: Extraction, source_type: str, filename_or_url: str
) -> ExtractResponse:
    text = neutralize_source_delimiters(extraction.text)
    warnings = list(extraction.warnings)
    warnings.extend(scan_for_injection(text))
    truncated = len(text) > MAX_EXTRACTED_CHARS
    if truncated:
        text = text[:MAX_EXTRACTED_CHARS]
        warnings.append(
            f"Extracted text was truncated to {MAX_EXTRACTED_CHARS} characters."
        )
    return ExtractResponse(
        text=text,
        source_type=source_type,
        filename_or_url=filename_or_url,
        char_count=len(text),
        truncated=truncated,
        warnings=list(dict.fromkeys(warnings)),
    )


@router.post("/extract", response_model=ExtractResponse)
async def extract_source(
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
):
    """Extract text from one supported upload or a public web URL."""
    if (file is None) == (url is None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one uploaded file or URL.",
        )

    if url is not None:
        try:
            extraction = await asyncio.to_thread(parser_service.parse_url, url)
        except ValueError as error:
            message = str(error)
            api_key = get_settings().gemini_api_key
            if api_key:
                message = message.replace(api_key, "[REDACTED]")
            logger.warning(
                "URL extraction rejected (%s): %s",
                type(error).__name__,
                message,
            )
            raise HTTPException(status_code=400, detail=message) from error
        except Exception as error:
            message = str(error)
            api_key = get_settings().gemini_api_key
            if api_key:
                message = message.replace(api_key, "[REDACTED]")
            logger.error(
                "URL extraction failed (%s): %s",
                type(error).__name__,
                message[:1000],
            )
            raise HTTPException(
                status_code=502,
                detail="Could not extract text from that URL.",
            ) from error
        return _trim_extraction(extraction, "url", url)

    assert file is not None
    filename = file.filename or "uploaded-file"
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The uploaded file exceeds the 10 MB limit.",
        )
    try:
        source_type, mime_type = _validate_uploaded_file(
            filename, file.content_type, file_bytes
        )
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    try:
        if source_type == "pdf":
            extraction = await parser_service.parse_pdf_with_fallback(file_bytes)
        elif source_type == "docx":
            extraction = await asyncio.to_thread(parser_service.parse_docx, file_bytes)
        elif source_type == "text":
            text = file_bytes.decode("utf-8-sig")
            extraction = Extraction(parser_service.parse_text(text))
        else:
            extraction = await parser_service.parse_image(file_bytes, mime_type)
    except Exception as error:
        settings = get_settings()
        safe_message = str(error)
        if settings.gemini_api_key:
            safe_message = safe_message.replace(
                settings.gemini_api_key, "[REDACTED]"
            )
        try:
            source_text = file_bytes.decode("utf-8-sig")
            if source_text:
                safe_message = safe_message.replace(
                    source_text, "[SOURCE REDACTED]"
                )
        except UnicodeDecodeError:
            pass
        logger.error(
            "File extraction failed (%s): %s",
            type(error).__name__,
            safe_message[:1000],
        )
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the uploaded file.",
        ) from error

    return _trim_extraction(extraction, source_type, filename)
