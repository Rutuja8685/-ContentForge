"""Content generation endpoints."""

import asyncio
import logging

from fastapi import APIRouter

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.services.llm_service import generate_output

logger = logging.getLogger(__name__)
router = APIRouter()


async def _generate_one(
    output_type: str, request: GenerateRequest
) -> tuple[str, dict | None, str | None]:
    try:
        result = await generate_output(output_type, request)
        return output_type, result, None
    except Exception as error:
        logger.warning(
            "Output generation failed for %s (%s)",
            output_type,
            type(error).__name__,
        )
        if isinstance(error, (RuntimeError, ValueError)):
            return output_type, None, str(error)
        return (
            output_type,
            None,
            "Generation failed unexpectedly. Please try again.",
        )


@router.post("", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate each requested output independently."""
    outcomes = await asyncio.gather(
        *(_generate_one(output_type, request) for output_type in request.output_types)
    )
    results = {output_type: result for output_type, result, _ in outcomes}
    errors = {
        output_type: error
        for output_type, _, error in outcomes
        if error is not None
    }
    return GenerateResponse(results=results, errors=errors)
