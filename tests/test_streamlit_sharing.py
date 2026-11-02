"""Tests that share links use the user's current editable text."""

from urllib.parse import unquote

import requests
from streamlit.testing.v1 import AppTest

class _Response:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "results": {
                "LinkedIn Post": {
                    "hook": "Initial hook",
                    "body": "Initial body",
                    "hashtags": ["InitialTag"],
                    "call_to_action": "Initial CTA",
                },
                "Twitter/X": {
                    "tweets": ["Initial tweet"],
                    "is_thread": False,
                    "hashtags": [],
                },
            },
            "errors": {},
        }


def test_linkedin_share_url_uses_edited_post_text(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *_args, **_kwargs: _Response())
    app = AppTest.from_file(
        "frontend/streamlit_app.py", default_timeout=30
    ).run()
    app.text_area(key="source_text").set_value("Source text")
    app.button(key="FormSubmitter:generate_form-Generate").click().run()

    edited = "नमस्कार! #Edited & ready\nSecond line"
    app.text_area(key="edit_LinkedIn Post").set_value(edited).run()
    linkedin_button = next(
        button
        for button in app.get("link_button")
        if button.label == "Post on LinkedIn"
    )

    assert unquote(linkedin_button.url.split("&text=", maxsplit=1)[1]) == edited


def test_x_share_link_uses_edited_tweet_and_overlong_tweet_disables_button(
    monkeypatch,
):
    monkeypatch.setattr(requests, "post", lambda *_args, **_kwargs: _Response())
    app = AppTest.from_file(
        "frontend/streamlit_app.py", default_timeout=30
    ).run()
    app.text_area(key="source_text").set_value("Source text")
    app.button(key="FormSubmitter:generate_form-Generate").click().run()

    edited = "नमस्कार #Edited & ready\nSecond line"
    app.text_area(key="edit_Twitter/X_1").set_value(edited).run()
    x_button = next(
        button
        for button in app.get("link_button")
        if button.label == "Post on X"
    )
    assert unquote(x_button.url.split("?text=", maxsplit=1)[1]) == edited

    app.text_area(key="edit_Twitter/X_1").set_value("x" * 281).run()
    assert any("over X's 280-character limit" in item.value for item in app.warning)
    assert any(
        button.label == "Post on X" and button.disabled
        for button in app.get("link_button")
    )


def test_empty_advisory_and_summary_lists_are_marked_in_display_and_editor(
    monkeypatch,
):
    class EmptyListsResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": {
                    "Advisory": {
                        "title": "Community update",
                        "severity": "Low",
                        "summary": "A program was announced.",
                        "affected_systems": [],
                        "impact": "No specific impact was reported.",
                        "recommended_actions": [],
                        "references": [],
                    },
                    "Executive Summary": {
                        "headline": "Community update",
                        "key_points": ["A program was announced."],
                        "risks": [],
                        "recommendations": [],
                    },
                },
                "errors": {},
            }

    monkeypatch.setattr(
        requests, "post", lambda *_args, **_kwargs: EmptyListsResponse()
    )
    app = AppTest.from_file(
        "frontend/streamlit_app.py", default_timeout=30
    ).run()
    app.text_area(key="source_text").set_value("Source text")
    app.button(key="FormSubmitter:generate_form-Generate").click().run()

    assert app.session_state["edit_Advisory"].count(
        "None identified in the source"
    ) == 3
    assert app.session_state["edit_Executive Summary"].count(
        "None identified in the source"
    ) == 2
    assert sum(
        item.value == "None identified in the source" for item in app.caption
    ) >= 5
