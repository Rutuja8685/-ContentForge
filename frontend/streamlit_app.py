"""Streamlit interface for generating LinkedIn posts."""

import requests
import streamlit as st

API_URL = "http://localhost:8000/generate"
OUTPUT_TYPES = ["LinkedIn Post"]

st.set_page_config(
    page_title="ContentForge",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ ContentForge")
st.subheader("Turn source material into polished LinkedIn content")

with st.form("generate_form"):
    source_text = st.text_area(
        "Source text",
        max_chars=20_000,
        height=220,
        help="Use only material you want transformed into a post.",
        key="source_text",
    )
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
        st.error("Enter source text before generating a post.")
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
        with st.spinner("Generating your content..."):
            try:
                response = requests.post(API_URL, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()
                st.session_state["generation_results"] = data.get("results", {})
                st.session_state["generation_errors"] = data.get("errors", {})
                st.session_state["last_request"] = payload
            except requests.ConnectionError:
                st.error(
                    "ContentForge could not reach the backend. Start the FastAPI "
                    "server and try again."
                )
            except requests.Timeout:
                st.error("The request timed out. Please try generating again.")
            except requests.HTTPError as error:
                st.error(
                    f"The backend returned an error "
                    f"({error.response.status_code}). Please try again."
                )
            except requests.RequestException:
                st.error("The request could not be completed. Please try again.")
            except ValueError:
                st.error("The backend returned an unreadable response.")

results = st.session_state.get("generation_results", {})
errors = st.session_state.get("generation_errors", {})

if results:
    st.subheader("Generated content")
    tabs = st.tabs(list(results))
    for tab, output_type in zip(tabs, results):
        with tab:
            result = results[output_type]
            if result is None:
                message = errors.get(output_type, "Generation failed.")
                if "GEMINI_API_KEY" in message:
                    st.error(
                        "Gemini is not configured on the backend. Add "
                        "GEMINI_API_KEY to the backend .env file and restart it."
                    )
                else:
                    st.error(message)
                continue

            st.markdown(f"### {result['hook']}")
            st.write(result["body"])
            hashtags = " ".join(
                f"#{tag.lstrip('#')}" for tag in result.get("hashtags", [])
            )
            st.markdown(hashtags)
            st.markdown(f"**Call to action:** {result['call_to_action']}")

            final_post = "\n\n".join(
                part
                for part in (
                    result["hook"],
                    result["body"],
                    hashtags,
                    result["call_to_action"],
                )
                if part
            )
            edit_key = f"edited_post_{output_type}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = final_post
            st.text_area(
                "Edit your final post",
                key=edit_key,
                height=240,
            )

            if st.button(
                "Regenerate",
                key=f"regenerate_{output_type}",
            ):
                last_request = st.session_state.get("last_request")
                if last_request is None:
                    st.error("Generate a post first, then try again.")
                else:
                    regenerate_payload = {
                        **last_request,
                        "output_types": [output_type],
                    }
                    with st.spinner("Regenerating your post..."):
                        try:
                            response = requests.post(
                                API_URL,
                                json=regenerate_payload,
                                timeout=120,
                            )
                            response.raise_for_status()
                            data = response.json()
                            new_result = data.get("results", {}).get(output_type)
                            st.session_state["generation_results"][output_type] = (
                                new_result
                            )
                            st.session_state["generation_errors"][output_type] = (
                                data.get("errors", {}).get(output_type, "")
                            )
                            if new_result is not None:
                                regenerated_text = "\n\n".join(
                                    part
                                    for part in (
                                        new_result["hook"],
                                        new_result["body"],
                                        " ".join(
                                            f"#{tag.lstrip('#')}"
                                            for tag in new_result.get("hashtags", [])
                                        ),
                                        new_result["call_to_action"],
                                    )
                                    if part
                                )
                                st.session_state[edit_key] = regenerated_text
                            st.rerun()
                        except requests.ConnectionError:
                            st.error(
                                "ContentForge could not reach the backend. "
                                "Start the FastAPI server and try again."
                            )
                        except requests.Timeout:
                            st.error("The request timed out. Please try again.")
                        except requests.HTTPError as error:
                            st.error(
                                f"The backend returned an error "
                                f"({error.response.status_code}). Please try again."
                            )
                        except requests.RequestException:
                            st.error("The request could not be completed.")
                        except ValueError:
                            st.error("The backend returned an unreadable response.")
else:
    for output_type, message in errors.items():
        st.error(f"{output_type}: {message}")
