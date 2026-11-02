"""Regression coverage for isolated Streamlit output regeneration."""

import requests
from streamlit.testing.v1 import AppTest


def _sample_results():
    return {
        "LinkedIn Post": {
            "hook": "Initial LinkedIn hook",
            "body": "Initial LinkedIn body",
            "hashtags": ["Community"],
            "call_to_action": "Share your thoughts.",
        },
        "Twitter/X": {
            "tweets": ["Initial tweet"],
            "is_thread": False,
            "hashtags": ["Community"],
        },
        "Advisory": {
            "title": "Initial advisory",
            "severity": "Low",
            "summary": "Initial summary",
            "affected_systems": ["Library"],
            "impact": "Initial impact",
            "recommended_actions": ["Collect feedback."],
            "references": [],
        },
        "Executive Summary": {
            "headline": "Initial summary headline",
            "key_points": ["Initial point"],
            "risks": [],
            "recommendations": [],
        },
    }


class _Response:
    status_code = 200

    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_regenerating_one_output_preserves_other_outputs_and_edits(monkeypatch):
    requests_made = []

    def fake_post(_url, json, timeout):
        requests_made.append(dict(json))
        if len(requests_made) == 1:
            return _Response({"results": _sample_results(), "errors": {}})

        output_type = json["output_types"][0]
        regenerated = dict(_sample_results()[output_type])
        regenerated["hook"] = "Regenerated LinkedIn hook"
        return _Response(
            {"results": {output_type: regenerated}, "errors": {}}
        )

    monkeypatch.setattr(requests, "post", fake_post)
    app = AppTest.from_file(
        "frontend/streamlit_app.py", default_timeout=30
    ).run()

    app.text_area(key="source_text").set_value("Original source text")
    app.button(key="FormSubmitter:generate_form-Generate").click().run()
    app.text_area(key="edit_Advisory").set_value(
        "Keep this Advisory edit"
    ).run()
    app.text_area(key="source_text").set_value("Changed form text")
    app.selectbox(key="tone").set_value("casual")
    app.run()
    app.button(key="regen_LinkedIn Post").click().run()

    assert requests_made[0]["output_types"] == [
        "LinkedIn Post",
        "Twitter/X",
        "Advisory",
        "Executive Summary",
    ]
    assert requests_made[1]["output_types"] == ["LinkedIn Post"]
    assert requests_made[1]["source_text"] == "Original source text"
    assert requests_made[1]["tone"] == "professional"
    assert (
        app.session_state["generation_results"]["LinkedIn Post"]["hook"]
        == "Regenerated LinkedIn hook"
    )
    assert app.session_state["edit_LinkedIn Post"] == (
        "Regenerated LinkedIn hook\n\nInitial LinkedIn body\n\n#Community"
        "\n\nShare your thoughts."
    )
    assert (
        app.session_state["saved_edited_content_Advisory"]
        == "Keep this Advisory edit"
    )
    assert (
        app.session_state["generation_results"]["Advisory"]["title"]
        == "Initial advisory"
    )
    assert (
        app.session_state["generation_results"]["Twitter/X"]["tweets"]
        == ["Initial tweet"]
    )
    assert (
        app.session_state["generation_results"]["Executive Summary"]["headline"]
        == "Initial summary headline"
    )
    assert not app.exception


def test_failed_regeneration_keeps_existing_result_and_user_edit(monkeypatch):
    requests_made = []

    def fake_post(_url, json, timeout):
        requests_made.append(dict(json))
        if len(requests_made) == 1:
            return _Response({"results": _sample_results(), "errors": {}})
        return _Response(
            {
                "results": {"LinkedIn Post": None},
                "errors": {
                    "LinkedIn Post": (
                        "Gemini is busy, wait a minute and click Regenerate"
                    )
                },
            }
        )

    monkeypatch.setattr(requests, "post", fake_post)
    app = AppTest.from_file(
        "frontend/streamlit_app.py", default_timeout=30
    ).run()
    app.text_area(key="source_text").set_value("Original source text")
    app.button(key="FormSubmitter:generate_form-Generate").click().run()
    app.text_area(key="edit_Advisory").set_value(
        "Keep this Advisory edit"
    ).run()
    app.button(key="regen_LinkedIn Post").click().run()

    assert requests_made[1]["output_types"] == ["LinkedIn Post"]
    assert (
        app.session_state["generation_results"]["LinkedIn Post"]["hook"]
        == "Initial LinkedIn hook"
    )
    assert (
        app.session_state["saved_edited_content_Advisory"]
        == "Keep this Advisory edit"
    )
    assert (
        app.session_state["generation_results"]["Advisory"]["title"]
        == "Initial advisory"
    )
    assert any("Gemini is busy" in error.value for error in app.error)
    assert not app.exception
