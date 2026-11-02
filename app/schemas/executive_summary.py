"""Structured schema for executive summaries."""

from pydantic import BaseModel


class ExecutiveSummary(BaseModel):
    """A concise summary for executive readers."""

    headline: str
    key_points: list[str]
    risks: list[str]
    recommendations: list[str]
