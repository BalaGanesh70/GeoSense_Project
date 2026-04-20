import html
import os
from typing import Any, Optional

import streamlit as st

from report_common import (
    get_report,
    render_disaster_label_natural_and_executive,
    render_inpage_qa_like_precautions,
    render_severity_at_glance,
    ZONE_JURISDICTION_SECTIONS,
)

st.set_page_config(page_title="Affected Regions", layout="wide")
st.title("Affected Regions")

# GeoSense project root (parent of /frontend)
_GEOSENSE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Zone id -> screenshot filename (place these PNGs in the project root or in assets/zones/)
_ZONE_SCREENSHOTS = [
    ("Zone-00", "Screenshot 2026-04-05 124836.png"),
    ("Zone-01", "Screenshot 2026-04-05 124859.png"),
    ("Zone-10", "Screenshot 2026-04-05 124913.png"),
    ("Zone-11", "Screenshot 2026-04-05 124927.png"),
]

_OVERALL_DONUT_COLORS = ["#0f766e", "#14b8a6", "#2dd4bf", "#0d9488", "#115e59", "#134e4a", "#5eead4", "#99f6e4"]
HIGH_RISK_THRESHOLD = 50.0

# Accent colours for zone ↔ state linkage cards
_ZONE_LINKAGE_ACCENTS: dict[str, str] = {
    "Zone-00": "#0284c7",
    "Zone-01": "#7c3aed",
    "Zone-10": "#059669",
    "Zone-11": "#d97706",
}


def _pie_colors(n: int, palette: list[str]) -> list[str]:
    if n <= 0:
        return []
    return [palette[i % len(palette)] for i in range(n)]


def _safe_key_fragment(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text)[:48]


def _filename_aliases(primary: str) -> list[str]:
    """Primary name plus underscore variant (e.g. Screenshot_2026-04-05_124836.png)."""
    aliases = [primary, primary.replace(" ", "_")]
    return list(dict.fromkeys(aliases))


def _damage_by_zone(regions: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in regions:
        if not isinstance(r, dict):
            continue
        z = str(r.get("zone", "")).strip()
        if not z:
            continue
        try:
            out[z] = float(r.get("damage", 0) or 0)
        except (TypeError, ValueError):
            out[z] = 0.0
    return out


def _format_zone_states_uts_cell(zone_id: str) -> str:
    """Single cell: labeled groups joined for the linkage table."""
    chunks: list[str] = []
    for title, names in ZONE_JURISDICTION_SECTIONS.get(zone_id, []):
        if names:
            chunks.append(f"{title}: {', '.join(names)}")
    return " · ".join(chunks) if chunks else "—"


def _jurisdiction_chips_html(zone_id: str) -> str:
    blocks: list[str] = []
    for title, names in ZONE_JURISDICTION_SECTIONS.get(zone_id, []):
        if not names:
            continue
        is_ut = "union" in title.lower()
        chip_bg = "#eef2ff" if is_ut else "#f1f5f9"
        chip_fg = "#3730a3" if is_ut else "#334155"
        chips = "".join(
            f'<span style="display:inline-block;background:{chip_bg};color:{chip_fg};'
            f"padding:5px 11px;border-radius:8px;margin:3px 5px 3px 0;font-size:0.8125rem;"
            f'border:1px solid rgba(15,23,42,0.06);">{html.escape(n)}</span>'
            for n in names
        )
        blocks.append(
            f'<div style="margin-top:10px;">'
            f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#64748b;margin-bottom:6px;">{html.escape(title)}</div>'
            f'<div style="line-height:1.45;">{chips}</div></div>'
        )
    return "".join(blocks) if blocks else '<span style="color:#94a3b8;font-size:0.9rem;">—</span>'


def _render_zone_state_linkage_section(dmg_map: dict[str, float], has_regions: bool) -> None:
    st.markdown(
        """
<style>
.linkage-wrap {
  background: linear-gradient(125deg, #f8fafc 0%, #eff6ff 42%, #faf5ff 100%);
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 1.35rem 1.5rem 1.15rem 1.5rem;
  margin-bottom: 1.1rem;
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
}
.linkage-wrap h2 {
  margin: 0 0 0.4rem 0;
  font-size: 1.4rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}
.linkage-wrap .sub {
  margin: 0 0 0.15rem 0;
  color: #64748b;
  font-size: 0.95rem;
  line-height: 1.45;
}
.linkage-wrap .hint {
  margin: 0.65rem 0 0 0;
  font-size: 0.78rem;
  color: #94a3b8;
}
</style>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="linkage-wrap">'
        "<h2>Zone ↔ state linkage</h2>"
        "<p class=\"sub\">Modelled <strong>damage %</strong> for each analysis zone, with "
        "states and union territories mapped to that zone. Bars scale to 100%.</p>"
        "<p class=\"hint\">Higher percentages indicate stronger inferred impact in that zone for this image.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns(2)
    for idx, (zid, _fname) in enumerate(_ZONE_SCREENSHOTS):
        solid = _ZONE_LINKAGE_ACCENTS.get(zid, "#64748b")
        d = dmg_map.get(zid)
        col = left_col if idx % 2 == 0 else right_col
        with col:
            with st.container(border=True):
                top = (
                    f'<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:2px;">'
                    f'<span style="background:{solid};color:#fff;padding:7px 16px;border-radius:999px;'
                    f'font-weight:700;font-size:0.95rem;box-shadow:0 2px 8px {solid}55;">{html.escape(zid)}</span>'
                )
                if d is not None:
                    top += (
                        f'<div style="text-align:right;">'
                        f'<div style="font-size:1.85rem;font-weight:800;color:{solid};line-height:1;">{d:.1f}%</div>'
                        f'<div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Model damage</div></div>'
                    )
                else:
                    top += (
                        '<div style="text-align:right;">'
                        '<div style="font-size:1.15rem;font-weight:600;color:#cbd5e1;">—</div>'
                        '<div style="font-size:0.68rem;color:#94a3b8;">No data</div></div>'
                    )
                top += "</div>"
                st.markdown(top, unsafe_allow_html=True)
                if d is not None:
                    st.progress(min(1.0, max(0.0, d / 100.0)))
                else:
                    st.progress(0)
                st.markdown(_jurisdiction_chips_html(zid), unsafe_allow_html=True)

    csv_lines = ["Zone,Model damage %,States and union territories"]
    for zid, _ in _ZONE_SCREENSHOTS:
        dm = dmg_map.get(zid)
        pct = f"{dm:.1f}" if dm is not None else ""
        cell = _format_zone_states_uts_cell(zid).replace('"', '""')
        csv_lines.append(f'"{zid}","{pct}","{cell}"')
    st.download_button(
        label="Download linkage as CSV",
        data="\n".join(csv_lines),
        file_name="zone_state_linkage.csv",
        mime="text/csv",
        key="download_zone_linkage_csv",
        help="Same data as the cards, for spreadsheets or reports.",
    )
    if not has_regions:
        st.info("Run analysis from the home page to fill in model damage percentages.")


def _resolve_zone_image(filename: str) -> Optional[str]:
    """Return first path that exists: project root, then assets/zones/."""
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


def _render_zone_damage_plots(sorted_regions: list[dict[str, Any]]) -> None:
    """Four Plotly views: bar, donut, radar, gauges."""
    categories = [str(r.get("zone", "")) for r in sorted_regions]
    values = [float(r.get("damage", 0) or 0) for r in sorted_regions]
    n_zones = len(values)
    max_dmg = max(values) if values else 0.0
    avg_dmg = sum(values) / n_zones if n_zones else 0.0
    high_risk_count = sum(1 for v in values if v >= HIGH_RISK_THRESHOLD)

    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        st.warning("Install plotly for all charts: `pip install plotly`")
        st.bar_chart({c: v for c, v in zip(categories, values)})
        return

    fig_bar = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker_color="#3498db",
                text=[f"{v:.0f}%" for v in values],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Damage: %{y:.1f}%<extra></extra>",
            )
        ]
    )
    fig_bar.update_layout(
        title="Zone-wise damage (bar)",
        xaxis_title="Zone",
        yaxis_title="Damage %",
        yaxis=dict(range=[0, max(100, max_dmg * 1.15)]),
        height=380,
        margin=dict(t=50, b=40),
        paper_bgcolor="white",
    )

    fig_pie = go.Figure(
        data=[
            go.Pie(
                labels=categories,
                values=values,
                hole=0.38,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Damage: %{value:.1f}%<br>Share: %{percent}<extra></extra>",
                marker=dict(
                    colors=_pie_colors(len(categories), _OVERALL_DONUT_COLORS),
                    line=dict(color="white", width=1.5),
                ),
            )
        ]
    )
    fig_pie.update_layout(
        title="Damage share by zone (donut)",
        height=380,
        margin=dict(t=50, b=20),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        paper_bgcolor="white",
    )

    r_closed = values + [values[0]] if values else []
    theta_closed = categories + [categories[0]] if categories else []
    fig_radar = go.Figure()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=r_closed,
            theta=theta_closed,
            fill="toself",
            fillcolor="rgba(46, 204, 113, 0.35)",
            line=dict(color="#27ae60", width=2),
            name="Damage %",
            hovertemplate="<b>%{theta}</b><br>Damage: %{r}%<extra></extra>",
        )
    )
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(0,0,0,0.12)"),
            angularaxis=dict(linecolor="rgba(0,0,0,0.2)"),
            bgcolor="rgba(248,249,250,0.9)",
        ),
        paper_bgcolor="white",
        height=380,
        margin=dict(t=50, b=40),
        showlegend=False,
        title=dict(text="Relative intensity (radar)", x=0.5, xanchor="center"),
    )

    fig_gauge = make_subplots(
        rows=1,
        cols=3,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
        horizontal_spacing=0.12,
    )
    fig_gauge.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=max_dmg,
            title={"text": "Max %"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#e74c3c"},
                "steps": [
                    {"range": [0, 33], "color": "#eafaf1"},
                    {"range": [33, 66], "color": "#fef9e7"},
                    {"range": [66, 100], "color": "#fdedec"},
                ],
            },
        ),
        row=1,
        col=1,
    )
    fig_gauge.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=round(avg_dmg, 1),
            title={"text": "Avg %"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#2980b9"},
                "steps": [
                    {"range": [0, 33], "color": "#eafaf1"},
                    {"range": [33, 66], "color": "#fef9e7"},
                    {"range": [66, 100], "color": "#fdedec"},
                ],
            },
        ),
        row=1,
        col=2,
    )
    fig_gauge.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=high_risk_count,
            title={"text": f"Zones ≥{HIGH_RISK_THRESHOLD:.0f}%"},
            number={"suffix": f" / {n_zones}"},
            gauge={
                "axis": {"range": [0, max(n_zones, 1)]},
                "bar": {"color": "#8e44ad"},
            },
        ),
        row=1,
        col=3,
    )
    fig_gauge.update_layout(
        height=380,
        margin=dict(t=50, b=20, l=30, r=30),
        paper_bgcolor="white",
        title=dict(text="Severity gauges", x=0.5, xanchor="center"),
    )

    r1c1, r1c2 = st.columns(2, gap="medium")
    with r1c1:
        st.plotly_chart(fig_bar, use_container_width=True)
    with r1c2:
        st.plotly_chart(fig_pie, use_container_width=True)
    r2c1, r2c2 = st.columns(2, gap="medium")
    with r2c1:
        st.plotly_chart(fig_radar, use_container_width=True)
    with r2c2:
        st.plotly_chart(fig_gauge, use_container_width=True)


analysis_data, report, regions = get_report()
affected = report.get("affected_regions", regions) or []

st.subheader("Zone map previews")
st.caption("Four analysis zones. Add the screenshot PNGs to the GeoSense project folder (or `assets/zones/`) using the exact filenames below.")

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
render_disaster_label_natural_and_executive(report)
render_severity_at_glance(
    regions,
    empty_message="No zone damage data yet. Run analysis from the home page to populate severity metrics.",
)

st.divider()
st.subheader("Zone-wise damage")
st.caption("Bar, donut, radar, and severity gauges from the current analysis.")

if regions:
    sorted_regions = sorted(regions, key=lambda r: r.get("damage", 0), reverse=True)
    _render_zone_damage_plots(sorted_regions)
else:
    st.info("No zone damage data yet. Run analysis from the home page to populate these charts.")

st.divider()
dmg_map = _damage_by_zone(regions) if regions else {}
_render_zone_state_linkage_section(dmg_map, bool(regions))

st.divider()
st.subheader("Select a zone")
zone_labels = [z for z, _ in _ZONE_SCREENSHOTS]
selected_zone = st.selectbox(
    "Choose a zone to view the full map crop",
    zone_labels,
    index=0,
    key="affected_region_zone_select",
)

fname = dict(_ZONE_SCREENSHOTS)[selected_zone]
detail_path = _resolve_zone_image(fname)

st.markdown(f"### {selected_zone}")
# Centered, compact preview (not full-width)
DETAIL_IMAGE_WIDTH_PX = 520
left_sp, mid, right_sp = st.columns([1, 2, 1])
with mid:
    if detail_path:
        st.image(detail_path, width=DETAIL_IMAGE_WIDTH_PX, use_container_width=False)
    else:
        st.warning(
            f"Image not found for **{selected_zone}**. Expected file name: `{fname}` "
            f"in `{_GEOSENSE_ROOT}` or `{os.path.join(_GEOSENSE_ROOT, 'assets', 'zones')}`."
        )

sections = ZONE_JURISDICTION_SECTIONS.get(selected_zone, [])
st.markdown(f"#### {selected_zone}: states and union territories")
zk = _safe_key_fragment(selected_zone)
for si, (group_title, names) in enumerate(sections):
    if not names:
        continue
    st.markdown(f"**{group_title}**")
    for name in names:
        st.checkbox(
            name,
            value=False,
            key=f"affected_chk_{zk}_{si}_{_safe_key_fragment(name)}",
        )

st.divider()
dn = (report.get("disaster_name") or "").strip() or "this disaster"
_affected_suggested = [
    f"How should I interpret zone damage percentages for **{selected_zone}** in this run?",
    f"Which states or union territories fall under **{selected_zone}**, and why does that matter?",
    f"What does the bar chart imply about relative risk across zones for **{dn}**?",
    f"How is the donut chart’s share by zone related to the bar heights?",
    f"What is the radar chart showing about **{selected_zone}** versus other zones?",
    f"How do the severity gauges relate to the **{HIGH_RISK_THRESHOLD:.0f}%** high-risk threshold?",
    f"What actions typically follow from a high damage reading in **{selected_zone}**?",
    f"How can I use the zone ↔ state linkage table in planning or reporting?",
    f"What caveats apply to modelled damage % from a single uploaded image?",
    f"How do I export or explain this page to a non-technical audience?",
]
ctx_affected = (
    f"affected_regions={affected}; selected_zone={selected_zone}; regions={regions}; "
    f"report_disaster_name={report.get('disaster_name', '')}; "
    f"executive_summary_excerpt={(report.get('summary') or '')[:800]}"
)
render_inpage_qa_like_precautions(
    tab_key="affected_regions",
    chat_session_key=f"chat_affected_regions_{selected_zone}",
    subheader="Affected regions Q&A",
    caption="Choose a suggested question or type your own. Answers use the selected zone and analysis context.",
    analysis_data=analysis_data,
    context_text=ctx_affected,
    suggested_questions=_affected_suggested,
    orange_button=True,
    selectbox_key=f"affected_qa_suggest_{selected_zone}",
    text_input_key=f"affected_qa_type_{selected_zone}",
    button_key=f"affected_qa_btn_{selected_zone}",
)
