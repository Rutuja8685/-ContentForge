"""LangChain-backed generators for supported output types."""

import asyncio
import logging
import re
from pathlib import Path
from typing import Type

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.generate import GenerateRequest
from app.schemas.linkedin import LinkedInPost

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
MAX_ATTEMPTS = 3

OUTPUT_REGISTRY: dict[str, tuple[Type[BaseModel], str]] = {
    "LinkedIn Post": (LinkedInPost, "linkedin.txt"),
}


def _http_status(error: Exception) -> int | None:
    """Find an HTTP status code without exposing exception contents to logs."""
    status = getattr(error, "status_code", None)
    if status is None:
        response = getattr(error, "response", None)
        status = getattr(response, "status_code", None)
    if status is not None:
        try:
            return int(status)
        except (TypeError, ValueError):
            return None

    match = re.search(r"\b(429|503)\b", str(error))
    return int(match.group(1)) if match else None


def _retryable(error: Exception) -> bool:
    return isinstance(error, OutputParserException) or _http_status(error) in {
        429,
        503,
    }


async def generate_output(
    output_type: str, request: GenerateRequest
) -> dict:
    """Generate and validate one output, retrying transient or parse failures."""
    registration = OUTPUT_REGISTRY.get(output_type)
    if registration is None:
        raise ValueError(f"Unsupported output type: {output_type}")

    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Add it to the project .env file "
            "and restart the backend."
        )

    schema, prompt_file = registration
    parser = PydanticOutputParser(pydantic_object=schema)
    prompt_text = (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
    prompt = PromptTemplate(
        template=prompt_text,
        input_variables=[
            "audience",
            "tone",
            "language",
            "detail_level",
            "objective",
            "style",
            "source_text",
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.7,
    )
    chain = prompt | model | parser

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await chain.ainvoke(
                {
                    "audience": request.audience,
                    "tone": request.tone,
                    "language": request.language,
                    "detail_level": request.detail_level,
                    "objective": request.objective,
                    "style": request.style,
                    "source_text": request.source_text,
                }
            )
            return result.model_dump()
        except Exception as error:
            if not _retryable(error):
                logger.error(
                    "Generation failed for %s (%s)",
                    output_type,
                    type(error).__name__,
                )
                raise RuntimeError(
                    "Generation failed while contacting Gemini. Please try again."
                ) from error

            status = _http_status(error)
            logger.warning(
                "Retryable generation failure for %s (attempt %d/%d, status=%s, type=%s)",
                output_type,
                attempt,
                MAX_ATTEMPTS,
                status if status is not None else "invalid-output",
                type(error).__name__,
            )
            if attempt == MAX_ATTEMPTS:
                if isinstance(error, OutputParserException):
                    raise RuntimeError(
                        "Gemini returned invalid structured data after 3 attempts."
                    ) from error
                raise RuntimeError(
                    f"Gemini request failed after 3 attempts (HTTP {status})."
                ) from error
            await asyncio.sleep(2 ** (attempt - 1))

    raise RuntimeError("Generation failed unexpectedly.")
