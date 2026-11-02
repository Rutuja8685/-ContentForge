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
    warnings: list[str] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    """Extracted source text and diagnostics returned by /upload/extract."""

    text: str
    source_type: str
    filename_or_url: str
    char_count: int
    truncated: bool
    warnings: list[str] = Field(default_factory=list)
