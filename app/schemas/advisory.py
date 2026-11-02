"""Structured schema for content advisories."""

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Supported advisory severity levels."""

    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class Advisory(BaseModel):
    """An advisory with impact and recommended actions."""

    title: str
    severity: Severity
    summary: str
    affected_systems: list[str]
    impact: str
    recommended_actions: list[str]
    references: list[str] = Field(default_factory=list)
