import html
import streamlit as st
import requests

HIGH_RISK_THRESHOLD = 50.0

# Four analysis zones: ordered sections (heading, unit names) for UI and docs.
ZONE_JURISDICTION_SECTIONS: dict[str, list[tuple[str, list[str]]]] = {
    "Zone-00": [
        ("States", ["West Bengal", "Odisha", "Bihar", "Jharkhand"]),
    ],
    "Zone-01": [
        ("States", ["Punjab", "Haryana", "Himachal Pradesh", "Uttarakhand", "Uttar Pradesh"]),
        ("Union Territories", ["Delhi", "Chandigarh", "Jammu and Kashmir", "Ladakh"]),
        ("States", ["Maharashtra", "Gujarat", "Rajasthan", "Goa"]),
        ("Union Territories", ["Dadra and Nagar Haveli and Daman and Diu"]),
    ],
    "Zone-10": [
        ("States", ["Tamil Nadu", "Kerala", "Karnataka", "Andhra Pradesh", "Telangana"]),
        ("Union Territories", ["Puducherry", "Lakshadweep"]),
    ],
    "Zone-11": [
        ("States", ["Assam", "Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Tripura", "Sikkim"]),
    ],
}


def render_zone_coverage_details() -> None:
    """States and UTs grouped by model zone (read-only reference above charts)."""
    st.subheader("Zone coverage (states and union territories)")
    st.caption("Geographic grouping used for the four analysis zones.")
    zone_order = ["Zone-00", "Zone-01", "Zone-10", "Zone-11"]
    row1a, row1b = st.columns(2)
    row2a, row2b = st.columns(2)
    cols = [row1a, row1b, row2a, row2b]
    for col, zid in zip(cols, zone_order):
        with col:
            with st.expander(zid, expanded=False):
                for title, names in ZONE_JURISDICTION_SECTIONS.get(zid, []):
                    st.markdown(f"**{title}**")
                    for n in names:
                        st.markdown(f"- {n}")


def executive_summary_one_liner(summary: str) -> str:
    one_liner = summary.replace("\n", " ").strip()
    if "." in one_liner:
        one_liner = one_liner.split(".")[0].strip() + "."
    elif len(one_liner) > 220:
        one_liner = one_liner[:217] + "…"
    return one_liner


def render_disaster_label_natural_and_executive(report: dict) -> None:
    """Single disaster label line and executive summary (Overview / Affected Regions)."""
    disaster_name = report.get("disaster_name", "") or "Unknown disaster"
    summary = (report.get("summary", "") or "").strip()
    one_liner = executive_summary_one_liner(summary)

    safe = html.escape(str(disaster_name))
    st.markdown(
        f'<p style="font-size:1.25rem;font-weight:600;color:#1f2937;margin-bottom:0.75rem;">'
        f"Disaster Label : <span style=\"color:#0f172a;\">{safe}</span></p>",
        unsafe_allow_html=True,
    )

    st.markdown("### Executive summary")
    st.caption(one_liner if one_liner else "No summary available from analysis.")
    if summary and len(summary) > len(one_liner):
        with st.expander("Full summary", expanded=False):
            st.write(summary)


def render_severity_at_glance(regions: list, *, empty_message: str | None = None) -> None:
    """Four metrics: max / average / high-risk count / zone count. Optional message when no regions."""
    if not regions:
        if empty_message:
            st.info(empty_message)
        return

    sorted_regions = sorted(regions, key=lambda r: r.get("damage", 0), reverse=True)
    values = [float(r.get("damage", 0) or 0) for r in sorted_regions]
    n_zones = len(values)
    max_dmg = max(values) if values else 0.0
    avg_dmg = sum(values) / n_zones if n_zones else 0.0
    high_risk_count = sum(1 for v in values if v >= HIGH_RISK_THRESHOLD)

    st.markdown("### Severity at a glance")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Max damage %", f"{max_dmg:.1f}", help="Highest zone damage")
    m2.metric("Average across zones", f"{avg_dmg:.1f}", help="Mean damage %")
    m3.metric(f"Zones ≥ {HIGH_RISK_THRESHOLD:.0f}%", str(high_risk_count), help="High-risk zone count")
    m4.metric("Zones analyzed", str(n_zones))


CORE_DISASTER_HAZARDS = ["Cyclone", "Rainfall", "Landslide", "Deforestation", "Earthquake"]

_HAZARD_RAINBOW_COLORS = [
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#bcf60c",
    "#fabed4",
    "#008080",
    "#9a6324",
    "#800000",
    "#808000",
    "#000075",
]


def _pie_colors_hazard(n: int, palette: list[str]) -> list[str]:
    if n <= 0:
        return []
    return [palette[i % len(palette)] for i in range(n)]


def _four_display_points_from_notes(notes: list) -> list[tuple[str, str]]:
    """Exactly 4 (line1, line2) pairs for 'About these plots' under Core Disaster Snapshot."""
    _fallback_pairs = [
        (
            "The bar chart ranks zones by inferred hazard impact (0–100%).",
            "Taller bars indicate zones where this hazard is modeled as relatively stronger.",
        ),
        (
            "The donut shows each zone’s share of total hazard impact.",
            "Larger slices correspond to higher bar values when all zones are included.",
        ),
        (
            "Compare the top bar with the largest slice to confirm the same dominant zone.",
            "Similar bar heights produce similar slice sizes in the donut.",
        ),
        (
            "Values are model- and context-based, not a substitute for field verification.",
            "Cross-check with local data, imagery, and official hazard products when possible.",
        ),
    ]
    out: list[tuple[str, str]] = []
    raw = [str(x).strip() for x in (notes or []) if str(x).strip()]
    for note in raw[:4]:
        lines = [ln.strip() for ln in note.replace("\r\n", "\n").split("\n") if ln.strip()]
        if len(lines) >= 2:
            out.append((lines[0], lines[1]))
        elif len(lines) == 1:
            s = lines[0]
            for sep in [". ", "? ", "! "]:
                pos = s.find(sep)
                if 12 <= pos <= len(s) - 8:
                    out.append((s[: pos + 1].strip(), s[pos + 1 :].strip()))
                    break
            else:
                out.append((s, "See the bar and donut charts for zone-level percentages."))
        else:
            out.append(_fallback_pairs[len(out) % 4])
    while len(out) < 4:
        out.append(_fallback_pairs[len(out) % 4])
    return out[:4]


def _join_plot_point_lines(line_a: str, line_b: str) -> str:
    """One display line per point (no mid-sentence line break)."""
    a, b = (line_a or "").strip(), (line_b or "").strip()
    if not b:
        return a
    if not a:
        return b
    if a[-1] in ".!?":
        return f"{a} {b}"
    return f"{a}. {b}"


def render_core_disaster_snapshot_section(
    report: dict,
    categories: list[str],
    values: list[float],
    *,
    selectbox_key: str,
    include_reasons_expanders: bool = True,
) -> None:
    """
    Core Disaster Snapshot: optional reasons expanders, hazard selectbox, bar + donut, plot notes.
    `categories` / `values` are zone damage from the current run (fallback when snapshot rows missing).
    """
    st.subheader("Core Disaster Snapshot")
    st.caption("Pick a hazard type to see zone-level inferred impact for that disaster (bar + donut + notes).")

    if include_reasons_expanders:
        reasons = report.get("reasons", []) or []
        if reasons:
            st.markdown("**Reasons / causes**")
            st.caption("Expand each item for detail from the analysis report.")
            for item in reasons:
                title = item.get("title") if isinstance(item, dict) else "Reason"
                desc = item.get("description") if isinstance(item, dict) else str(item)
                with st.expander(title or "Reason", expanded=False):
                    st.write(desc)
            st.markdown("")

    try:
        import plotly.graph_objects as go
    except ImportError:
        go = None  # type: ignore[assignment]

    snapshot = (report.get("core_disaster_snapshot") or {}) if isinstance(report, dict) else {}

    selected = st.selectbox(
        "Select hazard type",
        CORE_DISASTER_HAZARDS,
        index=0,
        help="Each hazard shows zone-level inferred impact for that disaster type (from analysis).",
        key=selectbox_key,
    )

    block = snapshot.get(selected) if isinstance(snapshot, dict) else None
    if not isinstance(block, dict):
        block = {"zone_impacts": [], "plot_notes": []}

    zone_rows = block.get("zone_impacts") or []
    zones_h = [str(r.get("zone", "")) for r in zone_rows if isinstance(r, dict)]
    impacts: list[float] = []
    for r in zone_rows:
        if isinstance(r, dict):
            try:
                impacts.append(float(r.get("impact_percent", 0) or 0))
            except (TypeError, ValueError):
                impacts.append(0.0)

    if len(zones_h) != len(impacts) or not zones_h:
        zones_h = list(categories)
        impacts = list(values)

    plot_notes = block.get("plot_notes") or block.get("insights") or []
    if not isinstance(plot_notes, list):
        plot_notes = []
    plot_notes = [str(x) for x in plot_notes if str(x).strip()]

    if not zones_h:
        st.info("No zone data available for hazard charts. Run analysis with valid zone damage first.")
        return

    if go is not None:
        st.markdown(f"**{selected}** — zone impact")

        hazard_bar_colors = _pie_colors_hazard(len(zones_h), _HAZARD_RAINBOW_COLORS)
        fig_h_bar = go.Figure(
            data=[
                go.Bar(
                    x=zones_h,
                    y=impacts,
                    marker_color=hazard_bar_colors,
                    text=[f"{v:.0f}%" for v in impacts],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Inferred impact: %{y:.1f}%<extra></extra>",
                )
            ]
        )
        fig_h_bar.update_layout(
            title=f"{selected}: inferred impact by zone",
            xaxis_title="Zone",
            yaxis_title="Impact % (hazard-specific)",
            yaxis=dict(range=[0, max(100, max(impacts) * 1.12) if impacts else 100]),
            height=360,
            margin=dict(t=50, b=40),
            paper_bgcolor="white",
        )

        fig_h_pie = go.Figure(
            data=[
                go.Pie(
                    labels=zones_h,
                    values=[max(v, 0.01) for v in impacts],
                    hole=0.35,
                    textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>Share of this hazard: %{percent}<extra></extra>",
                    marker=dict(
                        colors=_pie_colors_hazard(len(zones_h), _HAZARD_RAINBOW_COLORS),
                        line=dict(color="white", width=1.5),
                    ),
                )
            ]
        )
        fig_h_pie.update_layout(
            title=f"{selected}: share of hazard impact across zones",
            height=360,
            margin=dict(t=50, b=20),
            paper_bgcolor="white",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        )

        hc1, hc2 = st.columns(2, gap="medium")
        with hc1:
            st.plotly_chart(fig_h_bar, use_container_width=True)
        with hc2:
            st.plotly_chart(fig_h_pie, use_container_width=True)

        st.markdown("**About these plots**")
        st.caption(
            "Four bullet points for the selected hazard; each bullet is one full sentence combining bar and donut guidance."
        )
        point_pairs = _four_display_points_from_notes(plot_notes if plot_notes else [])
        bullet_block = "\n".join(
            f"- **Point {i}:** {_join_plot_point_lines(line_a, line_b)}"
            for i, (line_a, line_b) in enumerate(point_pairs, start=1)
        )
        st.markdown("\n" + bullet_block)
    else:
        st.warning("Install plotly for hazard charts: `pip install plotly`")
        st.bar_chart({z: v for z, v in zip(zones_h, impacts)})


def get_analysis_data():
    data = st.session_state.get("analysis_data")
    if not data:
        st.warning("No analysis found. Please analyze an image first.")
        st.page_link("app.py", label="Go to Upload Page", icon="🏠")
        st.stop()
    return data


def get_report():
    analysis_data = get_analysis_data()
    report = analysis_data.get("report", {}) or {}
    regions = analysis_data.get("regions", []) or []
    return analysis_data, report, regions


def _ensure_ten_suggested_questions(questions: list[str]) -> list[str]:
    """Pad or trim to exactly 10 suggested questions for in-page Q&A."""
    out = [str(q).strip() for q in questions if str(q).strip()]
    fillers = [
        "Summarize the key takeaway from this page in plain language.",
        "What limitations should I keep in mind when reading this view?",
        "How does this screen connect to the uploaded analysis?",
        "What would a responder typically do next after reviewing this?",
    ]
    i = 0
    while len(out) < 10:
        out.append(fillers[i % len(fillers)])
        i += 1
    return out[:10]


def render_inpage_qa_like_precautions(
    *,
    tab_key: str,
    chat_session_key: str,
    subheader: str,
    caption: str,
    analysis_data: dict,
    context_text: str,
    suggested_questions: list[str],
    question_suffix: str = "",
    orange_button: bool = True,
    selectbox_key: str,
    text_input_key: str,
    button_key: str,
) -> None:
    """
    Same interaction pattern as the Precautions page: chat history, 10 suggested questions,
    text input, and a full-width submit button (orange secondary by default).
    """
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = {}
    if chat_session_key not in st.session_state.chat_messages:
        st.session_state.chat_messages[chat_session_key] = []

    st.divider()
    st.subheader(subheader)
    st.caption(caption)

    for msg in st.session_state.chat_messages[chat_session_key]:
        role_label = "Question" if msg["role"] == "user" else "Answer"
        st.markdown(f"**{role_label}**\n\n{msg['content']}")
        st.markdown("---")

    ten_q = _ensure_ten_suggested_questions(suggested_questions)
    selected_suggestion = st.selectbox(
        "Possible questions (10)",
        ["Select a suggested question..."] + ten_q,
        index=0,
        key=selectbox_key,
    )

    typed_q = st.text_input(
        "Type your question",
        value="",
        key=text_input_key,
    )

    if orange_button:
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
        type="secondary" if orange_button else "primary",
        key=button_key,
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
        full_q = question_to_ask + (question_suffix or "")
        try:
            answer = call_chat(tab_key, full_q + "\n\nContext:\n" + context_text, analysis_data)
        except Exception as e:
            answer = f"Chat failed: {e}"

        st.session_state.chat_messages[chat_session_key].append({"role": "user", "content": question_to_ask})
        st.session_state.chat_messages[chat_session_key].append({"role": "assistant", "content": answer})
        st.rerun()


def call_chat(tab_key: str, question: str, analysis_data: dict) -> str:
    ctx = {
        "analysis_data": analysis_data,
        "tab_key": tab_key,
    }
    r = requests.post(
        "http://localhost:8000/chat",
        json={"question": question, "context": ctx},
        timeout=120,
    )
    r.raise_for_status()
    return r.json().get("answer", "")


def render_chat(tab_key: str, context_text: str, analysis_data: dict):
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = {}

    chat_key = f"chat_{tab_key}"
    if chat_key not in st.session_state.chat_messages:
        st.session_state.chat_messages[chat_key] = []

    for msg in st.session_state.chat_messages[chat_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_q = st.chat_input(f"Ask about this page ({tab_key})")
    if user_q:
        st.session_state.chat_messages[chat_key].append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.write(user_q)
        try:
            answer = call_chat(tab_key, user_q + "\n\nContext:\n" + context_text, analysis_data)
        except Exception as e:
            answer = f"Chat failed: {e}"
        st.session_state.chat_messages[chat_key].append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)

