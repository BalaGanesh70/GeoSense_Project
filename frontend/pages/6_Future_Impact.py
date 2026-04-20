import html
import os
import re
from typing import Optional

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from report_common import ZONE_JURISDICTION_SECTIONS, get_report, render_inpage_qa_like_precautions

st.set_page_config(page_title="Future Impact", layout="wide")
st.title("Future Impact")

_GEOSENSE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_ZONE_SCREENSHOTS = [
    ("Zone-00", "Screenshot 2026-04-05 124836.png"),
    ("Zone-01", "Screenshot 2026-04-05 124859.png"),
    ("Zone-10", "Screenshot 2026-04-05 124913.png"),
    ("Zone-11", "Screenshot 2026-04-05 124927.png"),
]

_ZONE_IDS = ["Zone-00", "Zone-01", "Zone-10", "Zone-11"]
_DISASTERS = ["Cyclone", "Earthquake", "Flood", "Landslide"]

_ZONE_SHORT = {
    "Zone-00": "eastern coastal belt (West Bengal, Odisha, Bihar, Jharkhand)",
    "Zone-01": "north–west and central India (incl. NCR, western states)",
    "Zone-10": "southern peninsula (TN, Kerala, Karnataka, AP, Telangana)",
    "Zone-11": "north-east region (eight states + connectivity constraints)",
}


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


def _risk_for_zone(future_rows: list, zone_id: str) -> Optional[str]:
    for row in future_rows:
        if not isinstance(row, dict):
            continue
        z = str(row.get("zone", "")).strip()
        if z == zone_id or zone_id in z or z in zone_id:
            return str(row.get("risk_level", "") or "").strip() or None
    return None


def _future_narrative_0_2(disaster: str, zone_id: str, risk: Optional[str]) -> str:
    zh = _ZONE_SHORT.get(zone_id, zone_id)
    r = (risk or "moderate").lower()
    d = disaster
    if disaster == "Cyclone":
        return (
            f"If a **{d}** affects **{zone_id}** ({zh}), the **0–2 year** window is dominated by emergency sheltering, "
            f"restoring power and communications, clearing debris, and disease-surveillance in crowded camps. "
            f"Modelled risk is treated as **{r}** for this zone: expect pressure on coastal embankments, agriculture "
            f"losses, and repeated seasonal exposure if cyclone season returns before full reconstruction."
        )
    if disaster == "Earthquake":
        return (
            f"After an **{d}** in **{zone_id}** ({zh}), years **0–2** focus on search-and-rescue completion, aftershock "
            f"safety, temporary housing, and rapid structural tagging of buildings. With risk context **{r}**, lifelines "
            f"(hospitals, roads, bridges) take priority; schools and markets reopen only after partial retrofit or "
            f"alternate sites are secured."
        )
    if disaster == "Flood":
        return (
            f"For **{d}** impacts in **{zone_id}** ({zh}), **0–2 years** typically involve pumping/drainage recovery, "
            f"contaminated-water mitigation, crop and livestock compensation cycles, and rebuilding low-lying assets. "
            f"Zone risk framing (**{r}**) implies recurring monsoon exposure, so early warning and embankment "
            f"maintenance compete with household-level elevation and insurance uptake."
        )
    # Landslide
    return (
        f"Following **{d}** in **{zone_id}** ({zh}), the **0–2 year** phase emphasizes slope stabilization, road reopening, "
        f"relocated settlements away from failure planes, and geotechnical monitoring. Interpreting risk as **{r}**, "
        f"intense rainfall can reactivate debris flows, so engineering works are paired with land-use controls and "
        f"community evacuation drills."
    )


def _future_narrative_2_5(disaster: str, zone_id: str, risk: Optional[str]) -> str:
    zh = _ZONE_SHORT.get(zone_id, zone_id)
    r = (risk or "moderate").lower()
    d = disaster
    if disaster == "Cyclone":
        return (
            f"In **2–5 years**, **{zone_id}** ({zh}) shifts toward resilient housing (roofing, anchoring), mangrove or "
            f"green-buffer restoration where feasible, and upgraded cyclone shelters aligned to population growth. "
            f"Economic recovery blends insurance markets with public works; risk **{r}** informs how much redundancy "
            f"(grids, logistics hubs) is justified before the next major season."
        )
    if disaster == "Earthquake":
        return (
            f"Years **2–5** for **{d}** in **{zone_id}** ({zh}) emphasize code-compliant rebuilds, school and hospital "
            f"retrofit programmes, and micro-zonation where data exists. With **{r}** risk, urban densification is "
            f"checked against liquefaction/soft-soil maps; supply chains and SMEs recover as commercial floorspace "
            f"returns and higher construction standards spread."
        )
    if disaster == "Flood":
        return (
            f"From **2–5 years**, **{zone_id}** ({zh}) invests in drainage master plans, nature-based buffers, and "
            f"flood-resilient livelihoods (elevated storage, alternate crops). Risk **{r}** guides whether relocation "
            f"or engineered protection dominates; institutions consolidate hydrology data and insurance penetration "
            f"so repeat floods do not erase gains."
        )
    return (
        f"**2–5 years** after **{d}** in **{zone_id}** ({zh}) deepens catchment management, terracing, subsurface drainage, "
        f"and long-term relocation for the highest-hazard pockets. With **{r}** risk, maintenance budgets and "
        f"community stewardship determine whether mitigation holds; transport corridors receive monitoring and "
        f"controlled cutting to reduce cascading failures."
    )


def _zone_tag(zone_id: str) -> str:
    return {
        "Zone-00": "coastal and delta-facing exposure",
        "Zone-01": "north–west / central urban and industrial corridors",
        "Zone-10": "southern peninsula monsoon and coastal–interior mix",
        "Zone-11": "north-east hills, rivers, and fragile transport links",
    }.get(zone_id, "this analysis zone")


def _build_precaution_points(disaster: str, zone_id: str, risk: Optional[str]) -> list[str]:
    """Five distinct before/during precaution lines for the selected disaster + zone."""
    zh = _ZONE_SHORT.get(zone_id, zone_id)
    zt = _zone_tag(zone_id)
    r = (risk or "moderate").lower()
    d = disaster
    dl = disaster.lower()

    if disaster == "Cyclone":
        return [
            f"Map cyclone shelters and evacuation routes for {zone_id} ({zh}); rehearse with household roles and contact trees.",
            f"Pre-landfall in {zone_id}: anchor roofs, clear drains, stock dry food/water/meds for 7–10 days given **{r}** risk framing.",
            f"During warnings, move inland and upward where {zt} applies; avoid coastal roads and vulnerable structures in {zone_id}.",
            f"Protect livestock and boats per local guidance; secure construction material that becomes wind-borne across {zone_id}.",
            f"Coordinate with ward officers and fishing societies in {zone_id} so last-mile alerts reach informal settlements.",
        ]
    if disaster == "Earthquake":
        return [
            f"Retrofit or brace heavy furniture and utilities in {zone_id} ({zh}); identify safe spots (drop–cover–hold) per room.",
            f"Keep shoes and torch by beds; gas shut-off awareness for {zone_id} buildings typical of **{zt}** construction patterns.",
            f"During shaking in {zone_id}: stay inside if safer than exit; avoid elevators, glass facades, and narrow stairwells.",
            f"Community drills for {dl} scenarios: assembly points away from façades and overhead wires in {zone_id}.",
            f"Pre-position medical caches and stretchers for {zone_id} clinics; align with district EMS plans for **{r}** exposure.",
        ]
    if disaster == "Flood":
        return [
            f"Elevate valuables and power strips in {zone_id} ({zh}); mark historical high-water lines using local flood memory.",
            f"Before monsoon peaks affecting {zt}, clear encroachments on drains and desilt neighborhood channels in {zone_id}.",
            f"During rise: avoid walking/driving through moving water; use mapped elevated corridors for {zone_id} evacuations.",
            f"Stock ORS, water purification, and insect protection for {zone_id}; plan for vector surge post-inundation.",
            f"Register vulnerable households in {zone_id} for priority rescue; align boats/rafts with **{r}** risk areas.",
        ]
    # Landslide
    return [
        f"Avoid new cuts on steep slopes in {zone_id} ({zh}); geoguide retaining and subsurface drainage where **{zt}** applies.",
        f"Early warning for intense rain: monitor cracks, tilted trees, and spring changes across {zone_id} slopes.",
        f"During failure risk: evacuate transverse valleys early; keep off roads under overhangs in {zone_id}.",
        f"Land-use rules in {zone_id}: relocate highest-risk pockets; stabilize headwater zones with bio-engineering where feasible.",
        f"Community lookouts and ham-radio/VHF nets for {zone_id} cut-off hamlets; rehearse vertical evacuation drills.",
    ]


def _build_postcaution_points(disaster: str, zone_id: str, risk: Optional[str]) -> list[str]:
    """Five distinct after-stage (post-caution) lines for the selected disaster + zone."""
    zh = _ZONE_SHORT.get(zone_id, zone_id)
    zt = _zone_tag(zone_id)
    r = (risk or "moderate").lower()
    dl = disaster.lower()

    if disaster == "Cyclone":
        return [
            f"After passage through {zone_id} ({zh}), document roof and embankment damage for relief; avoid wading in electrified floodwater.",
            f"Restore safe water and sanitation in shelters serving {zone_id}; watch for diarrhoeal and respiratory outbreaks.",
            f"Psychosocial first aid for children and elders in {zone_id}; reopen schools only after structural clearance.",
            f"Livelihood support for {zt} dependent workers (fisheries, agriculture) in {zone_id}; replace lost gear with safer designs.",
            f"Medium-term: rebuild to wind codes in {zone_id}; mangrove/coastal buffer plans where **{r}** seasonal return is likely.",
        ]
    if disaster == "Earthquake":
        return [
            f"Tag structures red/yellow/green in {zone_id} ({zh}) before re-entry; aftershock readiness for weeks.",
            f"Restore hospitals and blood banks first in {zone_id}; set up field triage for crush injuries typical of **{zt}**.",
            f"Temporary learning spaces for {zone_id} students; mental-health screening for first responders.",
            f"Retrofit public buildings and lifeline bridges in {zone_id}; soil maps guide where densification is unsafe.",
            f"Economic recovery: insurance and MSME credit lines for {zone_id}; update building bylaws with learned lessons.",
        ]
    if disaster == "Flood":
        return [
            f"Muck out homes safely in {zone_id} ({zh}); dry walls before mold; photograph losses for claims and relief.",
            f"Vector control and safe drinking water in {zone_id}; test wells after **{zt}** inundation patterns.",
            f"Restore markets and cold chains in {zone_id}; cash-for-work on drainage maintenance to reduce repeat damage.",
            f"Relocation dialogue for chronic inundation pockets in {zone_id}; combine engineering with nature-based buffers.",
            f"Hydrology dashboards for {zone_id} planners; insurance and crop diversification for **{r}** flood corridors.",
        ]
    return [
        f"Clear debris without destabilizing slopes in {zone_id} ({zh}); geotech sign-off before resettlement.",
        f"Restore footbridges and culverts serving {zone_id}; prioritize **{zt}** connectivity for health supply.",
        f"Terracing and subsurface drains in {zone_id} headwaters; community stewardship contracts for maintenance.",
        f"Long-run relocation for highest landslide runout zones in {zone_id}; avoid re-building on failure fans.",
        f"Monitoring networks and early warning SMS for {zone_id}; drill evacuations before each monsoon with **{r}** calibration.",
    ]


def _sentence_bullets(text: str, max_bullets: int = 4) -> list[str]:
    plain = text.replace("**", "")
    parts = re.split(r"(?<=[.!?])\s+", plain)
    return [p.strip() for p in parts if p.strip()][:max_bullets]


def _short_blurb(text: str, max_len: int = 240) -> str:
    plain = text.replace("**", "")
    if len(plain) <= max_len:
        return plain
    cut = plain[: max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def _road_timeline_figure_horizontal(
    phase1_title: str,
    phase1_desc: str,
    phase2_title: str,
    phase2_desc: str,
) -> go.Figure:
    """Left-to-right winding road; wide aspect for full-width layout."""
    n = 220
    x = np.linspace(0, 16, n)
    y = 0.42 * np.sin(x * 0.65) + 0.04 * x
    y = y - float(np.mean(y))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color="#111827", width=11),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    idx1 = int(n * 0.26)
    idx2 = int(n * 0.74)
    colors = ("#22c55e", "#1e3a8a")
    phases = (
        (idx1, "01", colors[0], phase1_title, phase1_desc),
        (idx2, "02", colors[1], phase2_title, phase2_desc),
    )

    y_rng = float(max(y) - min(y)) or 1.0
    for idx, num, col, ptitle, _ in phases:
        fig.add_trace(
            go.Scatter(
                x=[x[idx]],
                y=[y[idx]],
                mode="markers+text",
                marker=dict(size=42, color=col, line=dict(color="white", width=3)),
                text=[num],
                textposition="middle center",
                textfont=dict(color="white", size=16, family="Arial Black"),
                hovertemplate=f"<b>{ptitle}</b><extra></extra>",
                showlegend=False,
            )
        )
        short_lbl = "0–2 years" if num == "01" else "2–5 years"
        fig.add_annotation(
            x=x[idx],
            y=y[idx] + 0.42 * y_rng,
            text=short_lbl,
            showarrow=False,
            font=dict(size=13, color="#0f172a", family="Arial Black"),
            xanchor="center",
        )

    fig.update_layout(
        title=dict(text="Future impact roadmap (horizontal road timeline)", font=dict(size=17)),
        xaxis=dict(visible=False, range=[float(x[0]) - 0.6, float(x[-1]) + 0.6], fixedrange=True),
        yaxis=dict(visible=False, range=[float(min(y)) - 1.1 * y_rng, float(max(y)) + 1.4 * y_rng], fixedrange=True),
        margin=dict(l=24, r=24, t=56, b=28),
        height=300,
        autosize=True,
        paper_bgcolor="#f8fafc",
        plot_bgcolor="#f8fafc",
    )
    return fig


analysis_data, report, _ = get_report()
future_rows = report.get("future_impact", []) or []
if not isinstance(future_rows, list):
    future_rows = []

st.subheader("Disaster context")
selected_disaster = st.selectbox(
    "Select disaster",
    _DISASTERS,
    index=0,
    key="future_impact_disaster_selector",
)

report_name = (report.get("disaster_name") or "").strip()
if report_name and selected_disaster.lower() not in report_name.lower():
    st.caption(
        f"Analysis report is labeled **{report_name}**. "
        f"Precautions, post-cautions, and projections below follow **{selected_disaster}** and the **zone** you pick."
    )

st.subheader("Zone map previews")
st.caption("Four analysis zones for the selected disaster context.")

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

selected_zone = st.selectbox(
    "Select zone",
    _ZONE_IDS,
    index=0,
    key="future_impact_zone_selector",
    help="Future-impact text and the roadmap below update for this zone.",
)

with st.expander("Zone coverage (states and union territories)", expanded=False):
    for title, names in ZONE_JURISDICTION_SECTIONS.get(selected_zone, []):
        st.markdown(f"**{title}**")
        for n in names:
            st.markdown(f"- {n}")

risk_level = _risk_for_zone(future_rows, selected_zone)

st.subheader("Precautions and post-cautions")
st.caption(
    "Five points each, **specific to the disaster type and zone** you selected. "
    "Open the dropdown to see all five lines; pick one to show the full text below."
)

prec_points = _build_precaution_points(selected_disaster, selected_zone, risk_level)
post_points = _build_postcaution_points(selected_disaster, selected_zone, risk_level)

st.markdown(
    """
<style>
.fi-dd-lime { background: #ecfdf5; border-left: 6px solid #84cc16; padding: 0.75rem 1rem;
  border-radius: 8px; margin-bottom: 0.35rem; }
.fi-dd-blue { background: #eff6ff; border-left: 6px solid #1e3a8a; padding: 0.75rem 1rem;
  border-radius: 8px; margin-bottom: 0.35rem; }
.fi-dd-lime-body { background: #f0fdf4; border-left: 6px solid #84cc16; padding: 0.85rem 1rem;
  border-radius: 8px; color: #334155; font-size: 0.95rem; margin-top: 0.5rem; }
.fi-dd-blue-body { background: #f8fafc; border-left: 6px solid #2563eb; padding: 0.85rem 1rem;
  border-radius: 8px; color: #334155; font-size: 0.95rem; margin-top: 0.5rem; }
</style>
""",
    unsafe_allow_html=True,
)


dc1, dc2 = st.columns(2, gap="large")
with dc1:
    st.markdown(
        '<div class="fi-dd-lime"><strong style="color:#14532d;">Precautions (before & during)</strong><br/>'
        '<span style="color:#64748b;font-size:0.88rem;">Open the list to see all 5 points</span></div>',
        unsafe_allow_html=True,
    )
    prec_idx = st.selectbox(
        "Precautions",
        options=list(range(5)),
        format_func=lambda i: prec_points[i],
        key=f"future_prec_dd_{selected_disaster}_{selected_zone}",
        label_visibility="collapsed",
    )
    prec_sel = prec_points[prec_idx]
    st.markdown(
        f'<div class="fi-dd-lime-body">{html.escape(prec_sel)}</div>',
        unsafe_allow_html=True,
    )

with dc2:
    st.markdown(
        '<div class="fi-dd-blue"><strong style="color:#1e3a8a;">Post-cautions (after)</strong><br/>'
        '<span style="color:#64748b;font-size:0.88rem;">Open the list to see all 5 points</span></div>',
        unsafe_allow_html=True,
    )
    post_idx = st.selectbox(
        "Post-cautions",
        options=list(range(5)),
        format_func=lambda i: post_points[i],
        key=f"future_post_dd_{selected_disaster}_{selected_zone}",
        label_visibility="collapsed",
    )
    post_sel = post_points[post_idx]
    st.markdown(
        f'<div class="fi-dd-blue-body">{html.escape(post_sel)}</div>',
        unsafe_allow_html=True,
    )

st.subheader("Projected future effects if this disaster occurs")
st.caption(
    f"Zone **{selected_zone}** — inferred risk hint from report: **{risk_level or 'not specified per zone'}**."
)

fc1, fc2 = st.columns(2, gap="large")
with fc1:
    st.markdown("#### 0 to 2 years")
    st.write(_future_narrative_0_2(selected_disaster, selected_zone, risk_level))
with fc2:
    st.markdown("#### 2 to 5 years")
    st.write(_future_narrative_2_5(selected_disaster, selected_zone, risk_level))

if "future_impact_show_road" not in st.session_state:
    st.session_state.future_impact_show_road = False

_, btn_center, _ = st.columns([1, 2, 1])
with btn_center:
    if st.button(
        "Show road timeline",
        type="primary",
        key="future_impact_btn_show_road",
        use_container_width=True,
    ):
        st.session_state.future_impact_show_road = True

if st.session_state.future_impact_show_road:
    n0 = _future_narrative_0_2(selected_disaster, selected_zone, risk_level)
    n5 = _future_narrative_2_5(selected_disaster, selected_zone, risk_level)
    st.markdown("##### Road-style timeline (horizontal, full width)")
    st.caption(
        f"**{selected_disaster}** · **{selected_zone}** · risk hint: **{risk_level or 'not specified'}**"
    )

    p1_title = "0–2 years — response & early recovery"
    p1_short = _short_blurb(n0)
    p2_title = "2–5 years — resilience & longer recovery"
    p2_short = _short_blurb(n5)

    fig = _road_timeline_figure_horizontal(p1_title, p1_short, p2_title, p2_short)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Future impact roadmap — key points")
    st.caption("Two columns span the full content width: near-term (left) and medium-term (right).")

    bullets_0 = _sentence_bullets(n0, max_bullets=5)
    bullets_5 = _sentence_bullets(n5, max_bullets=5)
    if len(bullets_0) < 2:
        bullets_0 = [n0.replace("**", "")]
    if len(bullets_5) < 2:
        bullets_5 = [n5.replace("**", "")]

    full1, full2 = st.columns(2, gap="large")
    with full1:
        st.markdown(
            f'<div style="background:#ecfdf5;border-left:6px solid #22c55e;padding:1rem 1.1rem;border-radius:8px;min-height:12rem;">'
            f"<strong style='color:#14532d;font-size:1.05rem;'>01 — {html.escape(p1_title)}</strong><br/>"
            f"<span style='color:#334155;font-size:0.92rem;'>{html.escape(p1_short)}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Points**")
        for b in bullets_0:
            st.markdown(f"- {b}")
    with full2:
        st.markdown(
            f'<div style="background:#eff6ff;border-left:6px solid #1e3a8a;padding:1rem 1.1rem;border-radius:8px;min-height:12rem;">'
            f"<strong style='color:#1e3a8a;font-size:1.05rem;'>02 — {html.escape(p2_title)}</strong><br/>"
            f"<span style='color:#334155;font-size:0.92rem;'>{html.escape(p2_short)}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Points**")
        for b in bullets_5:
            st.markdown(f"- {b}")

st.divider()
_future_qa_suggested = [
    f"What are the main projected impacts for **{selected_disaster}** in **{selected_zone}** in years 0–2?",
    f"How do 2–5 year recovery priorities differ for **{selected_disaster}** in **{selected_zone}**?",
    f"How do the five precaution lines relate to **{selected_zone}** geography?",
    f"How do post-caution priorities change right after an event in **{selected_zone}**?",
    f"What does the risk hint **{risk_level or 'not specified'}** imply for this zone?",
    f"How should I read the horizontal road timeline versus the text summaries?",
    f"What investments reduce long-term losses for **{selected_disaster}** here?",
    f"Which institutions typically lead recovery for this kind of hazard in India?",
    f"What data gaps should I assume when using this Future Impact view?",
    f"How can I explain this page to community leaders in **{selected_zone}**?",
]
_ctx_future = (
    f"selected_disaster={selected_disaster}; selected_zone={selected_zone}; risk_level={risk_level}; "
    f"future_impact_rows={future_rows}; report_disaster_name={report.get('disaster_name', '')}; "
    f"zone_short={_ZONE_SHORT.get(selected_zone, '')}"
)
render_inpage_qa_like_precautions(
    tab_key="future_impact",
    chat_session_key=f"chat_future_impact_{selected_disaster}_{selected_zone}",
    subheader="Future impact Q&A",
    caption="Choose a suggested question or type your own. Answers use the selected disaster, zone, and risk context.",
    analysis_data=analysis_data,
    context_text=_ctx_future,
    suggested_questions=_future_qa_suggested,
    orange_button=True,
    selectbox_key=f"future_qa_suggest_{selected_disaster}_{selected_zone}",
    text_input_key=f"future_qa_type_{selected_disaster}_{selected_zone}",
    button_key=f"future_qa_btn_{selected_disaster}_{selected_zone}",
)
