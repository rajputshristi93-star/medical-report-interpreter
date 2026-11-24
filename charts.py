"""Charts that explain a report at a glance (Plotly)."""
from collections import Counter

import plotly.graph_objects as go

from i18n import t

COLORS = {"normal": "#2FBF71", "low": "#F5A623", "high": "#E5484D", "unknown": "#9AA7B2", "unverified": "#C3CBD3"}
ZONES = {"low": "rgba(245,166,35,.22)", "normal": "rgba(47,191,113,.28)", "high": "rgba(229,72,77,.20)"}
FONT = dict(family="Inter, Segoe UI, sans-serif", size=13, color="#1F3A44")


def _num(x):
    return isinstance(x, (int, float)) and x == x


def _layout(fig, height, **kw):
    fig.update_layout(height=height, margin=dict(l=10, r=20, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=FONT, hoverlabel=dict(font=FONT, bgcolor="white"), **kw)
    return fig


def status_donut(results):
    counts = Counter(str(r.get("status", "unknown")) for r in results)
    order = [s for s in ("normal", "low", "high", "unknown", "unverified") if counts[s]]
    fig = go.Figure(go.Pie(
        labels=[t(f"status.{s}") for s in order], values=[counts[s] for s in order], hole=0.64, sort=False,
        direction="clockwise", textinfo="value", textfont=dict(size=15, color="white"),
        marker=dict(colors=[COLORS[s] for s in order], line=dict(color="white", width=4)),
        pull=[0.05 if s in ("low", "high") else 0 for s in order],
        hovertemplate="%{label}: %{value} tests (%{percent})<extra></extra>"))
    judged = counts["normal"] + counts["low"] + counts["high"]
    centre = f"<b style='font-size:30px'>{counts['normal']}/{judged}</b><br>{t('ch.in_range')}" if judged else "-"
    fig.add_annotation(text=centre, showarrow=False, font=dict(size=14, color="#1F3A44"))
    fig.update_layout(legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"))
    return _layout(fig, 340)


def range_bars(results, limit=14):
    """One row per test that has both limits. The diamond shows where the value sits inside the range."""
    rows = []
    for r in results:
        lo, hi, v = r.get("ref_low"), r.get("ref_high"), r.get("value")
        if _num(lo) and _num(hi) and _num(v) and hi > lo and r.get("status") in ("normal", "low", "high"):
            pos = (v - lo) / (hi - lo)
            rows.append((r, pos))
    rows.sort(key=lambda t: (t[0]["status"] == "normal", -abs(t[1] - 0.5)))
    rows = rows[:limit][::-1]
    if not rows:
        return None
    fig = go.Figure()
    for i, (r, pos) in enumerate(rows):
        for (x0, x1), key in (((-0.6, 0), "low"), ((0, 1), "normal"), ((1, 1.6), "high")):
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=i - 0.28, y1=i + 0.28, fillcolor=ZONES[key], line_width=0, layer="below")
        shown = max(-0.55, min(1.55, pos))
        fig.add_trace(go.Scatter(
            x=[shown], y=[i], mode="markers", showlegend=False,
            marker=dict(symbol="diamond", size=17, color=COLORS[r["status"]], line=dict(color="white", width=2.5)),
            hovertemplate=(f"<b>{r['test']}</b><br>Your value: {r['value']:g} {r.get('unit', '')}<br>"
                           f"Normal range: {r['ref_low']:g} to {r['ref_high']:g}<extra></extra>")))
    for x, label in ((-0.3, t("ch.axis_low")), (0.5, t("ch.axis_normal")), (1.3, t("ch.axis_high"))):
        fig.add_annotation(x=x, y=len(rows) - 0.35, text=label, showarrow=False, font=dict(size=11, color="#5C7480"), yshift=14)
    fig.update_xaxes(range=[-0.6, 1.6], visible=False)
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(rows))), ticktext=[r["test"][:30] for r, _ in rows],
                     showgrid=False, zeroline=False, range=[-0.6, len(rows) + 0.2])
    return _layout(fig, 90 + 40 * len(rows))


def gap_bars(results, limit=12):
    """How far each abnormal value is outside its nearest limit, in percent."""
    items = []
    for r in results:
        v, lo, hi, s = r.get("value"), r.get("ref_low"), r.get("ref_high"), r.get("status")
        if s == "high" and _num(hi) and hi and _num(v):
            items.append((r, (v - hi) / abs(hi) * 100))
        elif s == "low" and _num(lo) and lo and _num(v):
            items.append((r, -(lo - v) / abs(lo) * 100))
    if not items:
        return None
    items = sorted(items, key=lambda t: abs(t[1]), reverse=True)[:limit][::-1]
    fig = go.Figure(go.Bar(
        y=[r["test"][:30] for r, _ in items], x=[d for _, d in items], orientation="h",
        marker=dict(color=[COLORS[r["status"]] for r, _ in items], line=dict(color="white", width=1.5)),
        text=[f"{d:+.0f}%" for _, d in items], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f}% outside the limit<extra></extra>"))
    fig.add_vline(x=0, line_color="#1F3A44", line_width=1.5)
    fig.update_xaxes(title=t("ch.gap_axis"), zeroline=False,
                     gridcolor="rgba(18,49,58,.08)")
    fig.update_yaxes(showgrid=False)
    return _layout(fig, 100 + 38 * len(items))


def _show(st, fig):
    cfg = {"displayModeBar": False}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=cfg)


def render_report_charts(results=None):
    """Charts for the results currently in this session."""
    import streamlit as st

    results = results if results is not None else st.session_state.get("results")
    if not results:
        return
    st.divider()
    st.markdown(f'<div class="t-eyebrow">{t("ch.eyebrow")}</div><div class="t-h1">{t("ch.title")}</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🍩 " + t("ch.tab1"), "📏 " + t("ch.tab2"), "📉 " + t("ch.tab3")])
    with t1:
        st.caption(t("ch.cap1"))
        _show(st, status_donut(results))
    with t2:
        st.caption(t("ch.cap2"))
        fig = range_bars(results)
        if fig is None:
            st.info(t("ch.need_limits"))
        else:
            _show(st, fig)
    with t3:
        st.caption(t("ch.cap3"))
        fig = gap_bars(results)
        if fig is None:
            st.success(t("ch.no_gaps"))
        else:
            _show(st, fig)
