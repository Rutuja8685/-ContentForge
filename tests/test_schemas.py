"""Validation tests for content generation schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.linkedin import LinkedInPost


def test_linkedin_post_accepts_valid_data():
    post = LinkedInPost(
        hook="A better way to collaborate",
        body="Teams can do more when they share knowledge.",
        hashtags=["Collaboration", "Leadership"],
        call_to_action="What has worked for your team?",
    )

    assert post.model_dump() == {
        "hook": "A better way to collaborate",
        "body": "Teams can do more when they share knowledge.",
        "hashtags": ["Collaboration", "Leadership"],
        "call_to_action": "What has worked for your team?",
    }


def test_linkedin_post_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        LinkedInPost(
            hook="A better way to collaborate",
            body="Teams can do more when they share knowledge.",
            hashtags=["Collaboration"],
        )


def test_linkedin_post_rejects_non_list_hashtags():
    with pytest.raises(ValidationError):
        LinkedInPost(
            hook="A better way to collaborate",
            body="Teams can do more when they share knowledge.",
            hashtags="Collaboration",
            call_to_action="Share your thoughts.",
        )
