"""Tests for transient Gemini request retries."""

import asyncio
from types import SimpleNamespace

import pytest
from langchain_core.runnables import RunnableLambda

import app.services.llm_service as llm_service
from app.schemas.generate import GenerateRequest


class QuotaError(Exception):
    status_code = 429


def test_rate_limit_retries_use_two_four_eight_second_backoff(monkeypatch):
    calls = []
    delays = []

    async def fail_with_quota(_prompt):
        calls.append(True)
        raise QuotaError("429 quota exceeded")

    async def record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(
        llm_service,
        "get_settings",
        lambda: SimpleNamespace(
            gemini_api_key="test-key-never-logged",
            gemini_model="test-model",
        ),
    )
    monkeypatch.setattr(
        llm_service,
        "ChatGoogleGenerativeAI",
        lambda **_kwargs: RunnableLambda(fail_with_quota),
    )
    monkeypatch.setattr(llm_service.asyncio, "sleep", record_sleep)

    request = GenerateRequest(
        source_text="A generic source paragraph.",
        output_types=["LinkedIn Post"],
        audience="community members",
        tone="professional",
        language="English",
        detail_level="standard",
        objective="inform",
        style="clear",
    )

    with pytest.raises(QuotaError):
        asyncio.run(llm_service.generate_output("LinkedIn Post", request))

    assert len(calls) == 4
    assert delays == [2, 4, 8]
