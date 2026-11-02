"""Tests for per-output provider errors from the generate endpoint."""

import logging

from app.routers import generate as generate_router


def test_quota_failure_returns_friendly_output_error_and_logs_reason(
    client, monkeypatch, caplog
):
    class QuotaProviderError(Exception):
        status_code = 429

    async def fail_generation(_output_type, _request):
        raise QuotaProviderError("429 RESOURCE_EXHAUSTED quota exceeded")

    monkeypatch.setattr(generate_router, "generate_output", fail_generation)
    caplog.set_level(logging.ERROR, logger="app.routers.generate")
    response = client.post(
        "/generate",
        json={
            "source_text": "A generic source paragraph.",
            "output_types": ["LinkedIn Post"],
            "audience": "community members",
            "tone": "professional",
            "language": "English",
            "detail_level": "standard",
            "objective": "inform",
            "style": "clear",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"]["LinkedIn Post"] is None
    assert body["errors"]["LinkedIn Post"] == (
        "Gemini is busy, wait a minute and click Regenerate"
    )
    assert "QuotaProviderError" in caplog.text
    assert "429 RESOURCE_EXHAUSTED quota exceeded" in caplog.text
