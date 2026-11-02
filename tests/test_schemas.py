"""Validation tests for content generation schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.advisory import Advisory, Severity
from app.schemas.executive_summary import ExecutiveSummary
from app.schemas.linkedin import LinkedInPost
from app.schemas.twitter import TwitterPost


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


def test_twitter_post_accepts_valid_data():
    post = TwitterPost(
        tweets=["A short post."],
        is_thread=False,
        hashtags=["Updates"],
    )

    assert post.tweets == ["A short post."]
    assert post.is_thread is False


def test_twitter_post_rejects_tweet_over_280_characters():
    with pytest.raises(ValidationError):
        TwitterPost(
            tweets=["x" * 281],
            is_thread=False,
            hashtags=[],
        )


def test_advisory_accepts_supported_severity():
    advisory = Advisory(
        title="Service update",
        severity="High",
        summary="A service issue was reported.",
        affected_systems=["Example service"],
        impact="Users may experience interruptions.",
        recommended_actions=["Monitor service status."],
        references=[],
    )

    assert advisory.severity == Severity.high


def test_advisory_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        Advisory(
            title="Service update",
            severity="Informational",
            summary="A service issue was reported.",
            affected_systems=["Example service"],
            impact="Users may experience interruptions.",
            recommended_actions=["Monitor service status."],
            references=[],
        )


def test_executive_summary_accepts_valid_data():
    summary = ExecutiveSummary(
        headline="A successful community initiative",
        key_points=["The program launched.", "Participants joined."],
        risks=["Participation may vary."],
        recommendations=["Continue gathering feedback."],
    )

    assert summary.headline == "A successful community initiative"
    assert summary.key_points[0] == "The program launched."
