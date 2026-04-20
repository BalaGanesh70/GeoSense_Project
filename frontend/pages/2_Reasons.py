import math

import streamlit as st

from report_common import get_report, render_core_disaster_snapshot_section

DISASTER_TYPES = ["Cyclone", "Rainfall", "Landslide", "Deforestation", "Earthquake"]
INFO_COLORS = ["#e53935", "#0b6fa4", "#e53935", "#0b6fa4", "#e53935"]


def _hazard_score(report: dict, hazard: str) -> float:
    """Average zone impact for one hazard (0-100)."""
    snapshot = (report.get("core_disaster_snapshot") or {}) if isinstance(report, dict) else {}
    block = snapshot.get(hazard) if isinstance(snapshot, dict) else None
    if not isinstance(block, dict):
        return 0.0
    rows = block.get("zone_impacts") or []
    vals: list[float] = []
    for r in rows:
        if isinstance(r, dict):
            try:
                vals.append(float(r.get("impact_percent", 0) or 0))
            except (TypeError, ValueError):
                vals.append(0.0)
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def _render_comparison_infographic(report: dict) -> None:
    st.markdown("---")
    st.subheader("Disaster Type Comparison")
    st.caption("Average modeled impact by disaster type using the same red/blue infographic pattern.")

    scores = [_hazard_score(report, h) for h in DISASTER_TYPES]
    center_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    try:
        import plotly.graph_objects as go

        left_col, chart_col, right_col = st.columns([1.1, 2.1, 1.1], gap="medium")

        def _side_item(label: str, value: float, color: str) -> None:
            st.markdown(
                f"""
<div style="border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;margin-bottom:10px;background:#ffffff;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <span style="font-size:0.9rem;font-weight:600;color:#111827;">{label}</span>
    <span style="font-size:0.9rem;font-weight:700;color:{color};">{value:.1f}%</span>
  </div>
  <div style="height:10px;background:#eef2f7;border-radius:999px;overflow:hidden;">
    <div style="height:10px;width:{max(1.0, min(100.0, value))}%;background:{color};border-radius:999px;"></div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

        with left_col:
            _side_item(DISASTER_TYPES[0], scores[0], INFO_COLORS[0])
            _side_item(DISASTER_TYPES[1], scores[1], INFO_COLORS[1])
        with right_col:
            _side_item(DISASTER_TYPES[2], scores[2], INFO_COLORS[2])
            _side_item(DISASTER_TYPES[3], scores[3], INFO_COLORS[3])
            _side_item(DISASTER_TYPES[4], scores[4], INFO_COLORS[4])

        # Center radial infographic
        fig = go.Figure()
        radius = 1.0
        angles = [math.radians(90 - i * (360 / len(DISASTER_TYPES))) for i in range(len(DISASTER_TYPES))]
        xs = [radius * math.cos(a) for a in angles]
        ys = [radius * math.sin(a) for a in angles]

        for x, y in zip(xs, ys):
            fig.add_trace(
                go.Scatter(
                    x=[0, x],
                    y=[0, y],
                    mode="lines",
                    line=dict(color="#d1d5db", width=2, dash="dot"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                marker=dict(size=48, color=INFO_COLORS, line=dict(color="white", width=2)),
                text=[f"{h}<br>{s:.1f}%" for h, s in zip(DISASTER_TYPES, scores)],
                textposition="middle center",
                textfont=dict(color="white", size=11),
                hovertemplate="<b>%{customdata}</b><extra></extra>",
                customdata=[f"{h}: {s:.1f}%" for h, s in zip(DISASTER_TYPES, scores)],
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[0],
                y=[0],
                mode="markers+text",
                marker=dict(size=70, color="#ef4444", line=dict(color="white", width=3)),
                text=[f"ALL<br>{center_score:.1f}%"],
                textposition="middle center",
                textfont=dict(color="white", size=16),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.update_layout(
            height=470,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(visible=False, range=[-1.45, 1.45]),
            yaxis=dict(visible=False, range=[-1.45, 1.45], scaleanchor="x", scaleratio=1),
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        with chart_col:
            st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("Install plotly for infographic chart: `pip install plotly`")
        st.dataframe(
            [{"Disaster": h, "Avg impact %": s} for h, s in zip(DISASTER_TYPES, scores)],
            use_container_width=True,
            hide_index=True,
        )

st.set_page_config(page_title="Reasons", layout="wide")
st.title("Reasons / Causes")

analysis_data, report, regions = get_report()
reasons = report.get("reasons", []) or []

sorted_regions = sorted(regions, key=lambda r: r.get("damage", 0), reverse=True) if regions else []
categories = [str(r.get("zone", "")) for r in sorted_regions]
values = [float(r.get("damage", 0) or 0) for r in sorted_regions]

if not regions:
    st.info("No zone damage data yet. Hazard charts need zone results from analysis.")
else:
    render_core_disaster_snapshot_section(
        report,
        categories,
        values,
        selectbox_key="reasons_core_disaster_hazard",
        include_reasons_expanders=False,
    )
    _render_comparison_infographic(report)
