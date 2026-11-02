"""Structured schema for Twitter/X posts and threads."""

from typing import Annotated

from pydantic import BaseModel, Field


class TwitterPost(BaseModel):
    """A Twitter/X post or thread with per-tweet length validation."""

    tweets: list[Annotated[str, Field(max_length=280)]] = Field(min_length=1)
    is_thread: bool
    hashtags: list[str]
