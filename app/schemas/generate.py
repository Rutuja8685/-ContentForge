"""Request and response models for content generation."""

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Input parameters shared by registered output generators."""

    source_text: str = Field(min_length=1, max_length=20_000)
    output_types: list[str] = Field(min_length=1)
    audience: str
    tone: str
    language: str
    detail_level: str
    objective: str
    style: str


class GenerateResponse(BaseModel):
    """Per-output results and errors from a generation request."""

    results: dict[str, dict | None]
    errors: dict[str, str]
