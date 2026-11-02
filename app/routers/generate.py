"""Content generation endpoints."""

import asyncio
import logging

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.generate import GenerateRequest, GenerateResponse
from app.services.security_service import (
    neutralize_source_delimiters,
    scan_for_injection,
)
from app.services.llm_service import generate_output, is_rate_limit_error

logger = logging.getLogger(__name__)
router = APIRouter()


async def _generate_one(
    output_type: str, request: GenerateRequest, semaphore: asyncio.Semaphore
) -> tuple[str, dict | None, str | None]:
    try:
        async with semaphore:
            result = await generate_output(output_type, request)
        return output_type, result, None
    except Exception as error:
        underlying = error.__cause__ or error
        message = str(underlying)
        settings = get_settings()
        if settings.gemini_api_key:
            message = message.replace(settings.gemini_api_key, "[REDACTED]")
        if request.source_text:
            message = message.replace(request.source_text, "[SOURCE REDACTED]")
        if "<source>" in message or "Treat everything inside" in message:
            message = "[prompt content redacted]"
        logger.exception(
            "Generation failed for %s (%s): %s",
            output_type,
            type(underlying).__name__,
            message,
            exc_info=False,
        )
        if is_rate_limit_error(underlying):
            return (
                output_type,
                None,
                "Gemini is busy, wait a minute and click Regenerate",
            )
        return (
            output_type,
            None,
            "Generation failed. Please check backend logs and retry.",
        )


@router.post("", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate each requested output independently."""
    warnings = scan_for_injection(request.source_text)
    request.source_text = neutralize_source_delimiters(request.source_text)
    logger.info("Generation requested for output types: %s", request.output_types)
    semaphore = asyncio.Semaphore(2)
    outcomes = await asyncio.gather(
        *(
            _generate_one(output_type, request, semaphore)
            for output_type in request.output_types
        )
    )
    results = {output_type: result for output_type, result, _ in outcomes}
    errors = {
        output_type: error
        for output_type, _, error in outcomes
        if error is not None
    }
    return GenerateResponse(results=results, errors=errors, warnings=warnings)
