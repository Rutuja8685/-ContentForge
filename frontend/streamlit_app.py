"""Streamlit interface for generating content in multiple formats."""

import requests
import streamlit as st

from frontend.share_links import (
    LINKEDIN_URL_LIMIT,
    build_linkedin_share_url,
    build_x_share_url,
)

API_URL = "http://localhost:8000/generate"
EXTRACT_URL = "http://localhost:8000/upload/extract"
OUTPUT_TYPES = [
    "LinkedIn Post",
    "Twitter/X",
    "Advisory",
    "Executive Summary",
]


def _list_content(items: list[str]) -> str:
    if not items:
        return "None identified in the source"
    return "\n".join(f"- {item}" for item in items)


def _render_list(title: str, items: list[str]) -> None:
    st.markdown(f"**{title}**")
    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.caption("None identified in the source")


def _final_text(output_type: str, result: dict) -> str:
    if output_type == "LinkedIn Post":
        hashtags = " ".join(
            f"#{tag.lstrip('#')}" for tag in result.get("hashtags", [])
        )
        return "\n\n".join(
            part
            for part in (
                result["hook"],
                result["body"],
                hashtags,
                result["call_to_action"],
            )
            if part
        )
    if output_type == "Twitter/X":
        tweets = "\n\n".join(
            f"Tweet {index}: {tweet}"
            for index, tweet in enumerate(result["tweets"], start=1)
        )
        hashtags = " ".join(f"#{tag.lstrip('#')}" for tag in result["hashtags"])
        return "\n\n".join(part for part in (tweets, hashtags) if part)
    if output_type == "Advisory":
        return "\n\n".join(
            (
                result["title"],
                f"Severity: {result['severity']}",
                result["summary"],
                "Affected systems:\n"
                + _list_content(result["affected_systems"]),
                f"Impact: {result['impact']}",
                "Recommended actions:\n"
                + _list_content(result["recommended_actions"]),
                "References:\n" + _list_content(result.get("references", [])),
            )
        )
    return "\n\n".join(
        (
            result["headline"],
            "Key points:\n" + "\n".join(f"- {item}" for item in result["key_points"]),
            "Risks:\n" + _list_content(result["risks"]),
            "Recommendations:\n"
            + _list_content(result["recommendations"]),
        )
    )


def _render_result(
    output_type: str, result: dict, has_error: bool = False
) -> None:
    if output_type == "LinkedIn Post":
        st.markdown(f"### {result['hook']}")
        st.write(result["body"])
        hashtags = " ".join(
            f"#{tag.lstrip('#')}" for tag in result.get("hashtags", [])
        )
        if hashtags:
            st.markdown(hashtags)
        st.markdown(f"**Call to action:** {result['call_to_action']}")
    elif output_type == "Twitter/X":
        st.markdown(
            f"**{'Thread' if result['is_thread'] else 'Single post'}**"
        )
        for index, tweet in enumerate(result["tweets"], start=1):
            with st.container(border=True):
                st.markdown(f"**Tweet {index}**")
                tweet_key = f"edit_Twitter/X_{index}"
                if tweet_key not in st.session_state:
                    st.session_state[tweet_key] = tweet
                st.text_area(
                    f"Edit tweet {index}",
                    key=tweet_key,
                    height=120,
                )
                edited_tweet = st.session_state[tweet_key]
                st.caption(f"{len(edited_tweet)} / 280 characters")
                if len(edited_tweet) > 280:
                    st.warning(
                        "This tweet is over X's 280-character limit; shorten it "
                        "before posting."
                    )
                st.link_button(
                    "Post on X",
                    build_x_share_url(edited_tweet),
                    disabled=has_error or len(edited_tweet) > 280,
                    key=f"post_x_{index}",
                )
        if result["hashtags"]:
            st.markdown(
                " ".join(f"#{tag.lstrip('#')}" for tag in result["hashtags"])
            )
    elif output_type == "Advisory":
        st.markdown(f"### {result['title']}")
        severity = result["severity"]
        severity_icon = {
            "Low": "⚪",
            "Medium": "🟡",
            "High": "🟠",
            "Critical": "🔴",
        }.get(severity, "")
        st.markdown(f"**Severity:** {severity_icon} {severity}")
        st.markdown("**Summary**")
        st.write(result["summary"])
        _render_list("Affected systems", result["affected_systems"])
        st.markdown("**Impact**")
        st.write(result["impact"])
        _render_list("Recommended actions", result["recommended_actions"])
        _render_list("References", result.get("references", []))
    else:
        st.markdown(f"### {result['headline']}")
        for title, key in (
            ("Key points", "key_points"),
        ):
            st.markdown(f"**{title}**")
            for item in result[key]:
                st.markdown(f"- {item}")
        _render_list("Risks", result["risks"])
        _render_list("Recommendations", result["recommendations"])


def _request_generation(payload: dict) -> dict | None:
    try:
        response = requests.post(API_URL, json=payload, timeout=420)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error(
            "ContentForge could not reach the backend. Start the FastAPI server "
            "and try again."
        )
    except requests.Timeout:
        st.error("The request timed out. Please try generating again.")
    except requests.HTTPError as error:
        if error.response.status_code == 429:
            st.error("Gemini is busy, wait a minute and click Regenerate")
        else:
            st.error(
                f"The backend returned an error ({error.response.status_code}). "
                "Please try again."
            )
    except requests.RequestException:
        st.error("The request could not be completed. Please try again.")
    except ValueError:
        st.error("The backend returned an unreadable response.")
    return None


def _extract_source(file=None, url: str | None = None) -> dict | None:
    try:
        if file is not None:
            response = requests.post(
                EXTRACT_URL,
                files={
                    "file": (
                        file.name,
                        file.getvalue(),
                        file.type or "application/octet-stream",
                    )
                },
                timeout=90,
            )
        else:
            response = requests.post(
                EXTRACT_URL,
                data={"url": url},
                timeout=20,
            )
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error("ContentForge could not reach the backend. Start FastAPI and retry.")
    except requests.Timeout:
        st.error("Source extraction timed out. Please try again.")
    except requests.HTTPError as error:
        try:
            detail = error.response.json().get("detail", "")
        except ValueError:
            detail = ""
        st.error(detail or "The source could not be extracted. Check the input and retry.")
    except requests.RequestException:
        st.error("Source extraction failed. Please try again.")
    except ValueError:
        st.error("The backend returned an unreadable extraction response.")
    return None


def _save_edited_content(output_type: str) -> None:
    edit_key = f"edit_{output_type}"
    st.session_state[f"saved_edited_content_{output_type}"] = st.session_state[
        edit_key
    ]


def _clear_source_metadata() -> None:
    st.session_state.pop("source_metadata", None)


def _clear_output_edit_state() -> None:
    for key in list(st.session_state):
        if (
            key.startswith("edit_")
            or key.startswith("tweet_")
            or key.startswith("saved_edited_content_")
        ):
            st.session_state.pop(key, None)


st.set_page_config(
    page_title="ContentForge",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ ContentForge")
st.subheader("Transform source material into polished content")

for pending_name, state_name in (
    ("pending_source_text", "source_text"),
    ("pending_source_metadata", "source_metadata"),
):
    if pending_name in st.session_state:
        st.session_state[state_name] = st.session_state.pop(pending_name)

paste_tab, file_tab, url_tab, image_tab = st.tabs(
    ["Paste text", "Upload file", "From URL", "Image"]
)
with paste_tab:
    st.text_area(
        "Source text",
        max_chars=20_000,
        height=220,
        help="Paste text here or review and edit extracted content.",
        key="source_text",
        on_change=_clear_source_metadata,
    )
with file_tab:
    uploaded_file = st.file_uploader(
        "Choose a PDF, DOCX, TXT, or MD file",
        type=["pdf", "docx", "txt", "md"],
        key="document_upload",
    )
    if st.button(
        "Extract file text",
        key="extract_document",
        disabled=uploaded_file is None,
    ):
        with st.spinner("Extracting text from the file..."):
            extraction = _extract_source(file=uploaded_file)
        if extraction is not None:
            st.session_state["pending_source_text"] = extraction["text"]
            st.session_state["pending_source_metadata"] = extraction
            st.rerun()
with url_tab:
    source_url = st.text_input(
        "Public web URL",
        placeholder="https://example.com/article",
        key="source_url",
    )
    if st.button(
        "Extract URL text",
        key="extract_url",
        disabled=not source_url.strip(),
    ):
        with st.spinner("Fetching and extracting the web page..."):
            extraction = _extract_source(url=source_url.strip())
        if extraction is not None:
            st.session_state["pending_source_text"] = extraction["text"]
            st.session_state["pending_source_metadata"] = extraction
            st.rerun()
with image_tab:
    uploaded_image = st.file_uploader(
        "Choose a PNG, JPG, or WEBP image",
        type=["png", "jpg", "jpeg", "webp"],
        key="image_upload",
    )
    if st.button(
        "Describe image and extract visible text",
        key="extract_image",
        disabled=uploaded_image is None,
    ):
        with st.spinner("Analyzing the image..."):
            extraction = _extract_source(file=uploaded_image)
        if extraction is not None:
            st.session_state["pending_source_text"] = extraction["text"]
            st.session_state["pending_source_metadata"] = extraction
            st.rerun()

source_metadata = st.session_state.get("source_metadata")
source_text_value = st.session_state.get("source_text", "")
if source_text_value:
    st.caption(
        f"Source: {source_metadata['source_type'] if source_metadata else 'text'} "
        f"· {len(source_text_value):,} characters"
    )
    if source_metadata and source_metadata["truncated"]:
        st.warning(
            "Extracted text was truncated to 20,000 characters. Review it before generating."
        )
    if source_metadata:
        for warning in source_metadata.get("warnings", []):
            st.warning(warning)

with st.form("generate_form"):
    source_text = st.session_state.get("source_text", "")
    selected_outputs = st.multiselect(
        "Output types",
        options=OUTPUT_TYPES,
        default=OUTPUT_TYPES,
        key="output_types",
    )

    tone_col, audience_col, language_col = st.columns(3)
    with tone_col:
        tone = st.selectbox(
            "Tone",
            ["professional", "casual", "formal", "persuasive", "informative"],
            key="tone",
        )
    with audience_col:
        audience = st.selectbox(
            "Audience",
            [
                "general public",
                "business professionals",
                "industry leaders",
                "customers",
                "students",
            ],
            key="audience",
        )
    with language_col:
        language = st.selectbox(
            "Language",
            ["English", "Hindi", "Marathi"],
            key="language",
        )

    detail_level = st.selectbox(
        "Detail level",
        ["brief", "standard", "detailed"],
        key="detail_level",
    )
    objective_col, style_col = st.columns(2)
    with objective_col:
        objective = st.text_input(
            "Objective",
            value="inform",
            max_chars=256,
            key="objective",
        )
    with style_col:
        style = st.text_input(
            "Style",
            value="clear and engaging",
            max_chars=128,
            key="style",
        )

    submitted = st.form_submit_button(
        "Generate",
        type="primary",
        disabled=not selected_outputs,
    )

if submitted:
    if not source_text.strip():
        st.error("Enter source text before generating content.")
    else:
        payload = {
            "source_text": source_text,
            "output_types": selected_outputs,
            "audience": audience,
            "tone": tone,
            "language": language,
            "detail_level": detail_level,
            "objective": objective,
            "style": style,
        }
        st.session_state["last_request"] = {
            **payload,
            "output_types": list(payload["output_types"]),
        }
        with st.spinner("Generating your content..."):
            data = _request_generation(payload)
        if data is not None:
            _clear_output_edit_state()
            st.session_state["generation_results"] = data.get("results", {})
            st.session_state["generation_errors"] = data.get("errors", {})
            st.session_state["generation_warnings"] = data.get("warnings", [])
            for warning in st.session_state["generation_warnings"]:
                st.warning(warning)
            for output_type in payload["output_types"]:
                result = st.session_state["generation_results"].get(output_type)
                if result is not None:
                    final_content = _final_text(output_type, result)
                    st.session_state[
                        f"saved_edited_content_{output_type}"
                    ] = final_content
                    st.session_state[f"edit_{output_type}"] = final_content
                else:
                    st.session_state[
                        f"saved_edited_content_{output_type}"
                    ] = ""
                    st.session_state[f"edit_{output_type}"] = ""

for output_type in st.session_state.pop("pending_regenerated_outputs", []):
    for key in list(st.session_state):
        if key == f"edit_{output_type}" or key.startswith(
            f"edit_{output_type}_"
        ):
            st.session_state.pop(key, None)
    st.session_state.pop(f"saved_edited_content_{output_type}", None)

results = st.session_state.get("generation_results", {})
generation_errors = st.session_state.get("generation_errors", {})

if results:
    st.subheader("Generated content")
    tabs = st.tabs(list(results))
    for tab, output_type in zip(tabs, results):
        with tab:
            result = results[output_type]
            error = generation_errors.get(output_type, "")
            if error:
                if "Gemini is busy" in error or "429" in error or "quota" in error.lower():
                    st.error("Gemini is busy, wait a minute and click Regenerate")
                else:
                    st.error(
                        f"{output_type} could not be generated. Check the backend "
                        "logs and try again."
                    )
            if result is None:
                if not error:
                    st.info("No generated content is available yet.")
                continue
            edit_key = f"edit_{output_type}"
            saved_edit_key = f"saved_edited_content_{output_type}"
            if saved_edit_key not in st.session_state:
                st.session_state[saved_edit_key] = _final_text(output_type, result)
            st.session_state[edit_key] = st.session_state[saved_edit_key]
            _render_result(output_type, result, has_error=bool(error))
            if output_type != "Twitter/X":
                st.text_area(
                    "Edit your final content",
                    key=edit_key,
                    height=260,
                    on_change=_save_edited_content,
                    args=(output_type,),
                )

            if output_type == "LinkedIn Post":
                edited_text = st.session_state[edit_key]
                linkedin_url = build_linkedin_share_url(edited_text)
                share_col, copy_col = st.columns([1, 2])
                with share_col:
                    st.link_button(
                        "Post on LinkedIn",
                        linkedin_url,
                        disabled=(
                            bool(error) or len(linkedin_url) > LINKEDIN_URL_LIMIT
                        ),
                        key="post_on_linkedin",
                    )
                    if len(linkedin_url) > LINKEDIN_URL_LIMIT:
                        st.warning(
                            "Too long for one-click share, use the copy box instead."
                        )
                with copy_col:
                    st.code(edited_text, language=None)
                    st.caption(
                        "If the text does not appear in LinkedIn, copy it from "
                        "here and paste it."
                    )
                st.caption(
                    "Opens LinkedIn/X with your text ready. Review it and click "
                    "Post yourself."
                )

            if output_type == "Twitter/X":
                st.caption(
                    "Opens LinkedIn/X with your text ready. Review it and click "
                    "Post yourself."
                )

            if st.button(
                "Regenerate",
                key=f"regen_{output_type}",
            ):
                last_request = st.session_state.get("last_request")
                if last_request is None:
                    st.error("Generate content first, then try again.")
                    continue
                regenerate_payload = {
                    **last_request,
                    "output_types": [output_type],
                }
                with st.spinner(f"Regenerating {output_type}..."):
                    data = _request_generation(regenerate_payload)
                if data is not None:
                    new_result = data.get("results", {}).get(output_type)
                    new_error = data.get("errors", {}).get(output_type)
                    if new_result is not None:
                        st.session_state["generation_results"][output_type] = (
                            new_result
                        )
                        st.session_state["generation_errors"].pop(
                            output_type, None
                        )
                        st.session_state["pending_regenerated_outputs"] = [
                            output_type
                        ]
                        st.rerun()
                    if new_error:
                        st.session_state["generation_errors"][output_type] = (
                            new_error
                        )
                        if (
                            "Gemini is busy" in new_error
                            or "429" in new_error
                            or "quota" in new_error.lower()
                        ):
                            st.error(
                                "Gemini is busy, wait a minute and click Regenerate"
                            )
                        else:
                            st.error(
                                f"{output_type} could not be regenerated. "
                                "Your existing content and edits are unchanged."
                            )
