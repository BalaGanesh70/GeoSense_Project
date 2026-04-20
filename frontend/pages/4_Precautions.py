import os
from typing import Optional

import streamlit as st

from report_common import call_chat, get_report

st.set_page_config(page_title="Precautions", layout="wide")
st.title("Precautions")

# GeoSense project root (parent of /frontend)
_GEOSENSE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Same zone screenshots as Affected Regions
_ZONE_SCREENSHOTS = [
    ("Zone-00", "Screenshot 2026-04-05 124836.png"),
    ("Zone-01", "Screenshot 2026-04-05 124859.png"),
    ("Zone-10", "Screenshot 2026-04-05 124913.png"),
    ("Zone-11", "Screenshot 2026-04-05 124927.png"),
]

_STAGE_OPTIONS = ["Before", "During", "After"]
_DISASTERS = ["Cyclone", "Earthquake", "Flood", "Landslide"]


def _filename_aliases(primary: str) -> list[str]:
    aliases = [primary, primary.replace(" ", "_")]
    return list(dict.fromkeys(aliases))


def _resolve_zone_image(filename: str) -> Optional[str]:
    subdirs = [
        _GEOSENSE_ROOT,
        os.path.join(_GEOSENSE_ROOT, "assets", "zones"),
    ]
    for name in _filename_aliases(filename):
        for base in subdirs:
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
    return None


analysis_data, report, _ = get_report()
precautions = report.get("precautions", {}) or {}

st.subheader("Disaster context")
selected_disaster = st.selectbox(
    "Select disaster",
    _DISASTERS,
    index=0,
    key="precaution_disaster_selector",
)

st.subheader("Zone map previews")
st.caption("Four analysis zones used for contextual precaution queries.")

cols = st.columns(4)
for col, (zone_id, fname) in zip(cols, _ZONE_SCREENSHOTS):
    with col:
        st.markdown(f"**{zone_id}**")
        path = _resolve_zone_image(fname)
        if path:
            st.image(path, use_container_width=True)
        else:
            st.info(f"Missing:\n`{fname}`")
            st.caption("Project root or assets/zones/")

st.divider()
st.subheader("Select stage")
selected_stage = st.radio(
    "Choose precaution stage",
    _STAGE_OPTIONS,
    horizontal=True,
    key="precaution_stage_selector",
)

stage_key_map = {"Before": "before", "During": "during", "After": "after"}
stage_key = stage_key_map[selected_stage]
stage_items = precautions.get(stage_key, []) or []


def _possible_questions(disaster: str, stage: str) -> list[str]:
    d = disaster.lower()

    if stage == "Before":
        return [
            f"What preparations should families complete before a {d} event?",
            f"How can people make their homes safer before a {d} occurs?",
            f"What emergency supplies should be stocked before the {d} risk period?",
            f"Which early warning signs and alerts should people monitor before a {d}?",
            f"How should evacuation planning be done before a {d} (routes, meeting points)?",
            f"What should elderly people and children prepare before a {d}?",
            f"How should communities coordinate assistance and communication before a {d}?",
            f"What precautions reduce injuries and damage before a {d} (inside vs outside)?",
            f"How can people protect water, food, and medication before a {d}?",
            f"What should authorities and local services ensure before {d} season/period?",
        ]

    if stage == "During":
        return [
            f"What should people do during a {d} event to stay safe?",
            f"What immediate actions are recommended when a warning is issued for {d}?",
            f"How should families respond during {d} while indoors vs outdoors?",
            f"What evacuation or shelter-in-place steps should be followed during {d}?",
            f"How should people protect themselves if they are unable to leave during {d}?",
            f"What should elderly people, children, and people with disabilities do during {d}?",
            f"How should communities coordinate support and prevent secondary hazards during {d}?",
            f"What to do if communication systems fail during {d}?",
            f"How should people manage medical needs and basic safety during {d}?",
            f"What steps should authorities take during {d} response and public guidance?",
        ]

    # After
    return [
        f"What immediate safety steps should people take after a {d} event?",
        f"How can residents check for and avoid hazards after a {d} (power, debris, floods)?",
        f"What should families do to restore safe water, food, and sanitation after {d}?",
        f"How should people handle injuries and access medical care after a {d}?",
        f"What guidance helps communities resume daily activities safely after {d}?",
        f"How should elderly people and vulnerable groups be supported after {d}?",
        f"How can locals verify information and avoid misinformation after {d}?",
        f"What precautions reduce disease outbreaks and contamination after {d}?",
        f"What actions should authorities prioritize for recovery after {d}?",
        f"How should people document damage and navigate recovery resources after {d}?",
    ]


st.divider()
st.subheader("Precaution Q&A")
st.caption(
    "Type a question or choose one from the list below, then click the button to get an answer. "
    "Responses use the selected disaster and stage."
)

chat_key = f"chat_precautions_{selected_disaster}_{stage_key}"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = {}
if chat_key not in st.session_state.chat_messages:
    st.session_state.chat_messages[chat_key] = []

for msg in st.session_state.chat_messages[chat_key]:
    role_label = "Question" if msg["role"] == "user" else "Answer"
    st.markdown(f"**{role_label}**\n\n{msg['content']}")
    st.markdown("---")

suggested = _possible_questions(selected_disaster, selected_stage)
selected_suggestion = st.selectbox(
    "Possible questions (10)",
    ["Select a suggested question..."] + suggested,
    index=0,
    key=f"precaution_question_suggestion_{selected_disaster}_{stage_key}",
)

typed_q = st.text_input(
    "Type your question",
    value="",
    key=f"precaution_typed_question_{selected_disaster}_{stage_key}",
)

st.markdown(
    """
<style>
div[data-testid="stButton"] > button[kind="secondary"] {
    background-color: #ea580c !important;
    color: #ffffff !important;
    border: none !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background-color: #c2410c !important;
    color: #ffffff !important;
}
</style>
""",
    unsafe_allow_html=True,
)
get_answer = st.button(
    "Click here to get the answer",
    use_container_width=True,
    type="secondary",
    key=f"precaution_get_answer_{selected_disaster}_{stage_key}",
)

question_to_ask = ""
if get_answer:
    if typed_q.strip():
        question_to_ask = typed_q.strip()
    elif selected_suggestion != "Select a suggested question...":
        question_to_ask = selected_suggestion
    else:
        st.warning("Type a question or select one from the list above.")

if question_to_ask:
    context_text = (
        f"selected_disaster={selected_disaster}; "
        f"selected_stage={selected_stage}; "
        f"stage_items={stage_items}; "
        f"all_precautions={precautions}; "
        f"report_disaster_name={report.get('disaster_name', '')}"
    )
    try:
        # Force a consistent, user-requested formatting for every answer.
        formatting_instructions = (
            "\n\nAnswer format requirements (follow strictly, no emojis):\n"
            "1) Provide 5 points using the exact format: `1) ...` `2) ...` ... `5) ...`.\n"
            "   - Each point must be bullet-like and about 2 lines (use a short newline inside each item).\n"
            "2) Below the 5 points, provide exactly 1 YouTube link relevant to the answer content.\n"
            "   - Use the label: `YouTube:` followed by the URL.\n"
            "3) Immediately below the YouTube link, provide 5 more points that describe/details what the YouTube link covers.\n"
            "   - Use the exact format again: `1) ...` `2) ...` ... `5) ...`.\n"
            "4) After those YouTube details points, provide exactly 3 reference links (websites/webpages/papers) relevant to the same content.\n"
            "   - Use the label: `References:` on its own line.\n"
            "   - Then provide exactly 3 URLs, one URL per line.\n"
            "5) For each reference URL, immediately below that URL, provide exactly 5 description points for that specific URL.\n"
            "   - Use the exact format again: `1) ...` `2) ...` ... `5) ...`.\n"
            "   - Repeat the 5-point description pattern separately for URL 1, URL 2, and URL 3.\n"
            "Do not add any extra sections beyond `YouTube:` and `References:` plus the points."
        )

        answer = call_chat(
            "precautions",
            question_to_ask + "\n\nContext:\n" + context_text + formatting_instructions,
            analysis_data,
        )
    except Exception as e:
        answer = f"Chat failed: {e}"

    st.session_state.chat_messages[chat_key].append({"role": "user", "content": question_to_ask})
    st.session_state.chat_messages[chat_key].append({"role": "assistant", "content": answer})
    st.rerun()
