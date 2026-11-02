"""Pydantic v2 schemas for all seven output types + shared request/response models."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


# ── Parameter enums ───────────────────────────────────────────────────────────

class Language(str, Enum):
    english = "English"
    hindi = "Hindi"
    marathi = "Marathi"


class DetailLevel(str, Enum):
    brief = "brief"
    standard = "standard"
    detailed = "detailed"


class Tone(str, Enum):
    professional = "professional"
    casual = "casual"
    formal = "formal"
    persuasive = "persuasive"
    informative = "informative"


# ── Generation parameters (shared across all output types) ────────────────────

class GenerationParams(BaseModel):
    target_audience: str = Field(default="general public", max_length=256)
    tone: Tone = Tone.professional
    language: Language = Language.english
    detail_level: DetailLevel = DetailLevel.standard
    communication_objective: str = Field(default="inform", max_length=256)
    content_style: str = Field(default="neutral", max_length=128)


# ── Output type enum ──────────────────────────────────────────────────────────

class OutputType(str, Enum):
    linkedin_post = "linkedin_post"
    twitter = "twitter"
    advisory = "advisory"
    executive_summary = "executive_summary"
    presentation = "presentation"
    video_package = "video_package"
    infographic = "infographic"


# ── Per-output Pydantic schemas ───────────────────────────────────────────────

class LinkedInPost(BaseModel):
    """Structured LinkedIn post output."""
    hook: str = Field(description="Attention-grabbing opening line")
    body: str = Field(description="Main body of the post (3-5 paragraphs)")
    hashtags: list[str] = Field(description="Relevant hashtags without #")
    call_to_action: str = Field(description="Clear CTA at the end of the post")


class Tweet(BaseModel):
    """A single tweet (<=280 chars)."""
    text: Annotated[str, Field(max_length=280)]
    hashtags: list[str] = Field(default_factory=list)


class TwitterThread(BaseModel):
    """Twitter/X thread or single tweet."""
    tweets: list[Tweet] = Field(description="Ordered list of tweets in the thread")


class AdvisorySeverity(str, Enum):
    critical = "Critical"
    high = "High"
    medium = "Medium"
    low = "Low"
    informational = "Informational"


class Advisory(BaseModel):
    """Security / compliance advisory."""
    title: str
    severity: AdvisorySeverity
    summary: str
    affected_systems: list[str]
    impact: str
    recommended_actions: list[str]
    references: list[str] = Field(default_factory=list)


class ExecutiveSummary(BaseModel):
    """C-suite executive summary."""
    headline: str
    key_points: list[str]
    risks: list[str]
    recommendations: list[str]


class Slide(BaseModel):
    title: str
    bullets: list[str]
    speaker_notes: str = ""


class Presentation(BaseModel):
    """Slide deck outline."""
    title: str
    slides: list[Slide]


class Scene(BaseModel):
    number: int
    description: str
    visuals: str
    narration: str


class VideoPackage(BaseModel):
    """Full video production package."""
    script: str
    storyboard: str
    scenes: list[Scene]
    subtitles: str
    visual_recommendations: str


class InfographicSection(BaseModel):
    heading: str
    content: str
    data_points: list[str] = Field(default_factory=list)


class Infographic(BaseModel):
    """Infographic content plan."""
    key_messaging: str
    sections: list[InfographicSection]
    layout_recommendation: str


# ── API request / response wrappers ───────────────────────────────────────────

class SourceType(str, Enum):
    text = "text"
    pdf = "pdf"
    docx = "docx"
    url = "url"
    image = "image"


class GenerateRequest(BaseModel):
    """Request body for POST /generate."""
    source_type: SourceType = SourceType.text
    source_text: str | None = Field(default=None, description="Pasted text content")
    source_url: str | None = Field(default=None, description="URL to fetch")
    output_types: list[OutputType] = Field(min_length=1)
    params: GenerationParams = Field(default_factory=GenerationParams)


class OutputResult(BaseModel):
    """A single generated output wrapped with metadata."""
    output_type: OutputType
    content: dict  # validated schema dict
    grounding_score: float | None = None
    flagged_claims: list[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    """Response envelope for POST /generate."""
    job_id: int
    results: list[OutputResult]


class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    created_at: str
    outputs: list[OutputResult] = Field(default_factory=list)
