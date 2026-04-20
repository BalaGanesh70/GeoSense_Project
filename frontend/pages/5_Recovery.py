import hashlib

import streamlit as st

from report_common import get_report, render_inpage_qa_like_precautions

st.set_page_config(page_title="Recovery", layout="wide")
st.title("Recovery")

analysis_data, report, _ = get_report()

DISASTERS = ["Cyclone", "Earthquake", "Flood", "Landslide"]

BUCKET_YEARS: dict[str, list[int]] = {
    "0-2": [1, 2],
    "2-5": [3, 4, 5],
    "5-10": [6, 7, 8, 9, 10],
}

BUCKET_LABEL = {
    "0-2": "0-2 years since event",
    "2-5": "2-5 years since event",
    "5-10": "5-10 years since event",
}

_MILESTONE_PALETTE = ["#facc15", "#fdba74", "#fb923c", "#ea580c", "#c2410c", "#92400e", "#713f12"]

DEATH_CAUSES = [
    "Person died due to no hospitals near",
    "Persons died due to No proper and Fast Emergency",
    "Person died due to No other person near to help",
    "Person died while taking to hospital",
]


def _disaster_seed(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16)


def _disaster_weights(disaster: str) -> tuple[float, float, float]:
    return {
        "Cyclone": (1.12, 1.05, 1.02),
        "Earthquake": (1.22, 1.6, 0.9),
        "Flood": (1.32, 1.12, 1.1),
        "Landslide": (1.05, 1.38, 0.86),
    }.get(disaster, (1.0, 1.0, 1.0))


def stats_for_recovery_year(disaster: str, rel_year: int) -> tuple[int, int, int]:
    seed = _disaster_seed(f"{disaster}|y{rel_year}")
    wi, wd, wr = _disaster_weights(disaster)
    base = 95 + (seed % 75) + rel_year * 22
    noise = 1.0 + ((seed >> 4) % 20) / 100.0
    injured = max(40, int(base * wi * noise))
    deaths = max(6, int(injured * (0.055 + (seed % 5) / 500) * wd))
    recovered = max(30, int(injured * (0.38 + 0.04 * rel_year) * wr + (seed % 35)))
    return injured, deaths, recovered


def _death_cause_weights(disaster: str, bucket: str) -> list[float]:
    base = {
        "Cyclone": [0.22, 0.33, 0.18, 0.27],
        "Earthquake": [0.28, 0.24, 0.21, 0.27],
        "Flood": [0.19, 0.36, 0.17, 0.28],
        "Landslide": [0.31, 0.22, 0.19, 0.28],
    }.get(disaster, [0.25, 0.25, 0.25, 0.25])
    shift = {
        "0-2": [0.00, 0.02, -0.01, -0.01],
        "2-5": [0.01, 0.00, 0.00, -0.01],
        "5-10": [0.02, -0.01, 0.01, -0.02],
    }[bucket]
    raw = [max(0.05, b + s) for b, s in zip(base, shift)]
    total = sum(raw)
    return [x / total for x in raw]


def _split_total_deaths(total_deaths: int, disaster: str, bucket: str) -> dict[str, int]:
    weights = _death_cause_weights(disaster, bucket)
    vals = [int(total_deaths * w) for w in weights]
    rem = max(0, total_deaths - sum(vals))
    for i in range(rem):
        vals[i % len(vals)] += 1
    return {cause: v for cause, v in zip(DEATH_CAUSES, vals)}


def _selected_cause_series(disaster: str, bucket: str, cause: str, years_in_bucket: list[int]) -> list[int]:
    idx = DEATH_CAUSES.index(cause)
    w = _death_cause_weights(disaster, bucket)[idx]
    out: list[int] = []
    for y in years_in_bucket:
        _inj, deaths, _rec = stats_for_recovery_year(disaster, y)
        out.append(max(1, int(deaths * w)))
    return out


if "recovery_year_bucket" not in st.session_state:
    st.session_state.recovery_year_bucket = "0-2"

st.markdown("### Recovery timeline (demo data)")
st.caption(
    "Choose a time window, then view timeline and per-year boxes. "
    "Counts are illustrative demo values for visualization."
)

selected = st.selectbox(
    "Select disaster",
    DISASTERS,
    index=0,
    key="recovery_disaster_select_main",
)

st.markdown("**Recovery window**")
b1, b2, b3 = st.columns(3)
bucket = st.session_state.recovery_year_bucket
with b1:
    if st.button("0-2 years", use_container_width=True, type="primary" if bucket == "0-2" else "secondary", key="rec_range_02"):
        st.session_state.recovery_year_bucket = "0-2"
        st.rerun()
with b2:
    if st.button("2-5 years", use_container_width=True, type="primary" if bucket == "2-5" else "secondary", key="rec_range_25"):
        st.session_state.recovery_year_bucket = "2-5"
        st.rerun()
with b3:
    if st.button("5-10 years", use_container_width=True, type="primary" if bucket == "5-10" else "secondary", key="rec_range_510"):
        st.session_state.recovery_year_bucket = "5-10"
        st.rerun()

bucket = st.session_state.recovery_year_bucket
years = BUCKET_YEARS[bucket]
n = len(years)
palette = [_MILESTONE_PALETTE[i % len(_MILESTONE_PALETTE)] for i in range(n)]

rows: list[dict] = []
for i, y in enumerate(years):
    injured, deaths, recovered = stats_for_recovery_year(selected, y)
    rows.append(
        {
            "idx": i + 1,
            "rel_year": y,
            "headline": f"Year {y}",
            "subtitle": BUCKET_LABEL[bucket],
            "injured": injured,
            "deaths": deaths,
            "recovered": recovered,
            "color": palette[i],
        }
    )

try:
    import plotly.graph_objects as go

    _plotly_ok = True
except ImportError:
    _plotly_ok = False

if _plotly_ok:
    xs = list(range(n))
    fig_tl = go.Figure()
    for i in range(n - 1):
        fig_tl.add_trace(
            go.Scatter(
                x=[i, i + 1],
                y=[0, 0],
                mode="lines",
                line=dict(color=palette[max(i, 0)], width=10),
                showlegend=False,
                hoverinfo="skip",
            )
        )
    if n == 1:
        fig_tl.add_trace(
            go.Scatter(x=[0, 0.001], y=[0, 0], mode="lines", line=dict(color=palette[0], width=10), showlegend=False, hoverinfo="skip")
        )

    fig_tl.add_trace(
        go.Scatter(
            x=xs,
            y=[0] * n,
            mode="markers+text",
            marker=dict(size=26, color=palette, line=dict(color="white", width=2)),
            text=[f"{r['idx']:02d}" for r in rows],
            textposition="top center",
            textfont=dict(size=14, color="#1e293b", family="Arial Black"),
            hovertemplate="<b>Milestone %{text}</b><br>%{customdata}<extra></extra>",
            customdata=[r["headline"] for r in rows],
        )
    )

    fig_tl.update_layout(
        title=f"{selected} - {BUCKET_LABEL[bucket]}",
        xaxis=dict(tickmode="array", tickvals=xs, ticktext=[f"{r['idx']:02d}\n{r['headline']}" for r in rows], showgrid=False),
        yaxis=dict(visible=False, range=[-0.35, 0.55]),
        height=200,
        margin=dict(l=40, r=40, t=70, b=70),
        paper_bgcolor="#fafafa",
        plot_bgcolor="#fafafa",
    )
    st.plotly_chart(fig_tl, use_container_width=True)

st.markdown("#### Year detail boxes")
for i, r in enumerate(rows):
    if i % 2 == 1:
        st.markdown('<div style="margin-top: 2.5rem;"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        head = (
            f'<div style="background:{r["color"]};color:#1e293b;padding:10px 14px;border-radius:8px 8px 0 0;'
            f'font-weight:700;font-size:1.05rem;">Milestone {r["idx"]:02d} - {r["headline"]}</div>'
        )
        st.markdown(head, unsafe_allow_html=True)
        st.caption(r["subtitle"])

        m1, m2, m3 = st.columns(3)
        m1.metric("Persons injured", f"{r['injured']:,}")
        m2.metric("Persons died", f"{r['deaths']:,}")
        m3.metric("Persons recovered", f"{r['recovered']:,}")

        if _plotly_ok:
            fig_mini = go.Figure(
                data=[
                    go.Bar(
                        x=["Injured", "Died", "Recovered"],
                        y=[r["injured"], r["deaths"], r["recovered"]],
                        marker_color=["#2563eb", "#dc2626", "#059669"],
                        text=[f"{r['injured']:,}", f"{r['deaths']:,}", f"{r['recovered']:,}"],
                        textposition="inside",
                        textfont=dict(color="#ffffff", size=12),
                        hovertemplate="%{x}: %{y:,}<extra></extra>",
                    )
                ]
            )
            fig_mini.update_layout(
                height=260,
                margin=dict(l=40, r=20, t=30, b=40),
                yaxis_title="Persons",
                showlegend=False,
                paper_bgcolor="white",
                plot_bgcolor="#f8fafc",
                title=dict(text=f"Year {r['rel_year']} breakdown", font=dict(size=14)),
            )
            st.plotly_chart(fig_mini, use_container_width=True)

st.markdown("---")
tot_inj = sum(r["injured"] for r in rows)
tot_dth = sum(r["deaths"] for r in rows)
tot_rec = sum(r["recovered"] for r in rows)
t1, t2, t3 = st.columns(3)
t1.metric("Window total injured", f"{tot_inj:,}")
t2.metric("Window total deaths", f"{tot_dth:,}")
t3.metric("Window total recovered", f"{tot_rec:,}")

st.markdown("---")
st.markdown("### Death-cause flow analysis")
st.caption(
    "For the selected window, total death count is split across four causes. "
    "Choose a cause to inspect yearly variation."
)

cause_disaster = st.selectbox(
    "Disaster for death-cause split",
    DISASTERS,
    index=DISASTERS.index(selected),
    key="recovery_cause_disaster_select",
    help="Defaults to the disaster selected above; you can compare with others.",
)
selected_cause = st.selectbox(
    "Select death-cause scenario",
    DEATH_CAUSES,
    index=0,
    key="recovery_death_cause_select",
)

cause_split = _split_total_deaths(tot_dth, cause_disaster, bucket)
selected_cause_yearly = _selected_cause_series(cause_disaster, bucket, selected_cause, years)

if _plotly_ok:
    side_left, middle, side_right = st.columns([1.05, 1.1, 1.05], gap="medium")

    # Left chart: selected-cause deaths by year
    with side_left:
        fig_left = go.Figure(
            data=[
                go.Bar(
                    x=[f"Y{y}" for y in years],
                    y=selected_cause_yearly,
                    marker_color=["#f59e0b", "#8b5cf6", "#3b82f6", "#ef4444", "#14b8a6"][: len(years)],
                    text=[f"{v:,}" for v in selected_cause_yearly],
                    textposition="outside",
                    textfont=dict(color="#111827", size=11),
                    hovertemplate="%{x}<br>Deaths: %{y:,}<extra></extra>",
                )
            ]
        )
        fig_left.update_layout(
            title="Selected cause by year",
            height=360,
            margin=dict(l=22, r=10, t=45, b=25),
            paper_bgcolor="white",
            plot_bgcolor="#f8fafc",
            yaxis=dict(rangemode="tozero"),
            showlegend=False,
        )
        st.plotly_chart(fig_left, use_container_width=True)

    with middle:
        # Center cards + circular count chart
        st.markdown(
            f"""
<div style="border:1px solid #e5e7eb;border-radius:12px;padding:14px 14px 10px 14px;background:white;margin-bottom:10px;">
  <div style="font-size:1.25rem;font-weight:700;color:#ef4444;">{cause_disaster}</div>
  <div style="font-size:0.95rem;color:#334155;">{selected_cause}</div>
  <div style="margin-top:8px;font-size:0.85rem;color:#64748b;">Window: {BUCKET_LABEL[bucket]}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        selected_count = cause_split[selected_cause]
        pct = (selected_count / max(tot_dth, 1)) * 100.0

        fig_mid = go.Figure(
            data=[
                go.Pie(
                    labels=["Selected cause", "Other causes"],
                    values=[selected_count, max(0, tot_dth - selected_count)],
                    hole=0.72,
                    marker=dict(colors=["#ef4444", "#e5e7eb"]),
                    textinfo="none",
                    hovertemplate="%{label}: %{value:,}<extra></extra>",
                    sort=False,
                )
            ]
        )
        fig_mid.add_annotation(
            x=0.5,
            y=0.54,
            text=f"<b>{selected_count:,}</b>",
            showarrow=False,
            font=dict(size=30, color="#111827"),
        )
        fig_mid.add_annotation(
            x=0.5,
            y=0.40,
            text=f"{pct:.1f}% of window deaths",
            showarrow=False,
            font=dict(size=12, color="#64748b"),
        )
        fig_mid.update_layout(
            title="Count at center",
            height=340,
            margin=dict(l=10, r=10, t=45, b=10),
            paper_bgcolor="white",
            showlegend=False,
        )
        st.plotly_chart(fig_mid, use_container_width=True)

    # Right chart: all causes compared
    with side_right:
        right_vals = [cause_split[c] for c in DEATH_CAUSES]
        fig_right = go.Figure(
            data=[
                go.Bar(
                    x=["No hospital", "No emergency", "No helper", "Transport"],
                    y=right_vals,
                    marker_color=["#f59e0b", "#8b5cf6", "#3b82f6", "#ef4444"],
                    text=[f"{v:,}" for v in right_vals],
                    textposition="outside",
                    textfont=dict(color="#111827", size=11),
                    hovertemplate="%{x}<br>Deaths: %{y:,}<extra></extra>",
                )
            ]
        )
        fig_right.update_layout(
            title="All causes comparison",
            height=360,
            margin=dict(l=22, r=10, t=45, b=25),
            paper_bgcolor="white",
            plot_bgcolor="#f8fafc",
            yaxis=dict(rangemode="tozero"),
            showlegend=False,
        )
        st.plotly_chart(fig_right, use_container_width=True)
else:
    st.warning("Install plotly for timeline charts: `pip install plotly`")
    st.dataframe(
        [{"Cause": k, "Count": v} for k, v in cause_split.items()],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
_recovery_suggested = [
    f"What do the milestone boxes represent for **{selected}** in the **{BUCKET_LABEL[bucket]}** window?",
    f"How should I read injured vs deaths vs recovered counts for **{selected}** here?",
    f"Why do death-cause splits change when I switch disaster type for the flow analysis?",
    f"What does the selected death-cause bar chart by year tell me?",
    f"How is the center donut count related to total deaths in this window?",
    f"What is the “all causes comparison” chart useful for?",
    f"Are these numbers forecasts or demo illustrations for the UI?",
    f"How can I relate this recovery view to real post-disaster reporting?",
    f"What limitations should I assume for these demo statistics?",
    f"What questions should I ask local authorities that this page cannot answer?",
]
_ctx_recovery = (
    f"disaster={selected}; bucket={bucket}; bucket_label={BUCKET_LABEL[bucket]}; milestones={rows}; "
    f"cause_disaster={cause_disaster}; cause_split={cause_split}; selected_cause={selected_cause}; "
    f"cause_series_yearly={selected_cause_yearly}; window_total_deaths={tot_dth}; "
    f"report_disaster_name={report.get('disaster_name', '')}"
)
render_inpage_qa_like_precautions(
    tab_key="recovery_after",
    chat_session_key=f"chat_recovery_{selected}_{bucket}_{cause_disaster}",
    subheader="Recovery Q&A",
    caption="Choose a suggested question or type your own. Context includes the selected disaster, window, and death-cause view.",
    analysis_data=analysis_data,
    context_text=_ctx_recovery,
    suggested_questions=_recovery_suggested,
    orange_button=False,
    selectbox_key=f"recovery_qa_suggest_{selected}_{bucket}",
    text_input_key=f"recovery_qa_type_{selected}_{bucket}",
    button_key=f"recovery_qa_btn_{selected}_{bucket}",
)
