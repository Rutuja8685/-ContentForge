"""LangChain-backed generators for supported output types."""

import asyncio
import json
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
from app.schemas.advisory import Advisory
from app.schemas.executive_summary import ExecutiveSummary
from app.schemas.generate import GenerateRequest
from app.schemas.linkedin import LinkedInPost
from app.schemas.twitter import TwitterPost

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
MAX_RETRIES = 3

OUTPUT_REGISTRY: dict[str, tuple[Type[BaseModel], str]] = {
    "LinkedIn Post": (LinkedInPost, "linkedin.txt"),
    "Twitter/X": (TwitterPost, "twitter.txt"),
    "Advisory": (Advisory, "advisory.txt"),
    "Executive Summary": (ExecutiveSummary, "executive_summary.txt"),
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
    return (
        isinstance(error, (OutputParserException, json.JSONDecodeError))
        or _http_status(error) in {429, 503}
    )


def is_rate_limit_error(error: Exception) -> bool:
    """Identify rate-limit and quota failures from provider exceptions."""
    current: BaseException | None = error
    while current is not None:
        status = _http_status(current) if isinstance(current, Exception) else None
        message = str(current).lower()
        if status == 429 or any(
            marker in message
            for marker in (
                "quota",
                "resource_exhausted",
                "rate limit",
                "too many requests",
            )
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


def _safe_error_message(error: Exception, request: GenerateRequest) -> str:
    """Return provider diagnostics without API keys or submitted prompt text."""
    message = str(error)
    api_key = get_settings().gemini_api_key
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    if request.source_text:
        message = message.replace(request.source_text, "[SOURCE REDACTED]")
    return message[:2000]


def _response_text(content: object) -> str:
    """Convert provider response content into text for structured parsing."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item["text"]
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        )
    return str(content)


def _extract_json(text: str) -> str:
    """Remove markdown fences and surrounding prose from a model response."""
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        return text[start : end + 1]
    return text.strip()


def _overlong_tweets(data: object) -> list[tuple[int, int]]:
    if not isinstance(data, dict):
        return []
    tweets = data.get("tweets")
    if not isinstance(tweets, list):
        return []
    return [
        (index, len(tweet))
        for index, tweet in enumerate(tweets, start=1)
        if isinstance(tweet, str) and len(tweet) > 280
    ]


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
    if not settings.gemini_model:
        raise RuntimeError(
            "GEMINI_MODEL is not configured. Add it to the project .env file "
            "and restart the backend."
        )

    schema, prompt_file = registration
    parser = PydanticOutputParser(pydantic_object=schema)
    prompt_text = (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
    prompt = PromptTemplate(
        template=prompt_text,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.7,
        timeout=60,
    )
    chain = prompt | model
    input_values = {
        "audience": request.audience,
        "tone": request.tone,
        "language": request.language,
        "detail_level": request.detail_level,
        "objective": request.objective,
        "style": request.style,
        "source_text": request.source_text,
    }
    retry_instruction = ""
    repair_attempted = False
    retry_count = 0

    while retry_count <= MAX_RETRIES:
        try:
            prompt_values = dict(input_values)
            if "repair_instruction" in prompt.input_variables:
                prompt_values["repair_instruction"] = retry_instruction
            response = await chain.ainvoke(prompt_values)
            raw_output = _response_text(response.content)
            json_output = _extract_json(raw_output)

            if output_type == "Twitter/X":
                decoded_output = json.loads(json_output)
                overlong = _overlong_tweets(decoded_output)
                if overlong:
                    if repair_attempted:
                        raise ValueError(
                            "Twitter/X reply still contains tweets over 280 characters."
                        )
                    repair_attempted = True
                    retry_instruction = (
                        "Your previous response had tweet(s) "
                        + ", ".join(
                            f"{index} ({length} characters)"
                            for index, length in overlong
                        )
                        + " over the 280-character limit. Rewrite those tweets "
                        "so each is 280 characters or fewer, preserving only "
                        "supported facts, and return the complete corrected "
                        "structured result."
                    )
                    continue

            return parser.parse(json_output).model_dump()
        except Exception as error:
            if not _retryable(error):
                raise

            status = _http_status(error)
            retrying = retry_count < MAX_RETRIES
            logger.warning(
                "Generation %s for %s (attempt %d, retries %d/%d, "
                "status=%s, type=%s): %s",
                "retrying" if retrying else "exhausted retries",
                output_type,
                retry_count + 1,
                retry_count,
                MAX_RETRIES,
                status if status is not None else "invalid-output",
                type(error).__name__,
                _safe_error_message(error, request),
            )
            if not retrying:
                raise
            retry_count += 1
            await asyncio.sleep(2 ** retry_count)

    raise RuntimeError("Generation failed unexpectedly.")
