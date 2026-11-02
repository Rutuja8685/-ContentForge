"""Structured schema for generated LinkedIn posts."""

from pydantic import BaseModel, Field


class LinkedInPost(BaseModel):
    """A LinkedIn post composed of its core publishing elements."""

    hook: str = Field(description="Attention-grabbing opening line")
    body: str = Field(description="Main post body")
    hashtags: list[str] = Field(description="Relevant hashtags without #")
    call_to_action: str = Field(description="Clear call to action")
