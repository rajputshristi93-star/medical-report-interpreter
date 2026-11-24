"""Result cards and the results hero. Used by the Interpreter results screen and by the home page preview."""
import html

from i18n import t

esc = html.escape


def marker_pos(v, lo, hi):
    """Where the dot sits on the bar: 0 to 25 low zone, 25 to 75 normal zone, 75 to 100 high zone."""
    if lo is not None and hi is not None and hi > lo:
        if v < lo:
            pos = 25 * max(0.0, 1 - (lo - v) / max(abs(lo), 1e-9))
        elif v > hi:
            pos = 75 + 25 * min(1.0, (v - hi) / max(abs(hi), 1e-9))
        else:
            pos = 25 + 50 * (v - lo) / (hi - lo)
    elif hi is not None:
        pos = 75 * max(0.0, v) / hi if v <= hi and hi > 0 else 75 + 25 * min(1.0, (v - hi) / max(abs(hi), 1e-9))
    elif lo is not None:
        pos = 25 + 75 * min(1.0, (v - lo) / max(abs(lo), 1e-9)) if v >= lo else 25 * max(0.0, 1 - (lo - v) / max(abs(lo), 1e-9))
    else:
        return None
    return min(97.0, max(3.0, pos))


def g(x):
    return f"{x:g}" if isinstance(x, (int, float)) and x == x else ("" if x is None else str(x))


def card_html(r, i):
    status = str(r.get("status", "unknown"))
    extreme = r.get("flag") == "extreme"
    cls = {"high": "hi", "low": "lo", "normal": "ok"}.get(status, "un")
    pill = t(f"status.{status}") if status in ("low", "normal", "high", "unknown", "unverified") else status
    pill_html = f'<span class="pl {"ex" if extreme else cls}">{esc(pill)}{" · " + esc(t("rs.extreme_tag")) if extreme else ""}</span>'
    lo, hi, v = r.get("ref_low"), r.get("ref_high"), r.get("value")
    numeric = isinstance(v, (int, float))
    pos = marker_pos(v, lo, hi) if numeric and status in ("low", "normal", "high") else None
    if pos is None:
        bar = '<div class="zb none"><i></i><i></i><i></i></div>'
        labels = f'<div class="zl" style="grid-template-columns:1fr"><span style="color:#5C7480">{esc(t("rs.unv_note") if status == "unverified" else t("rs.no_range"))}</span></div>'
    else:
        bar = f'<div class="zb"><i></i><i></i><i></i><span class="mk {cls}" style="left:{pos:.1f}%"></span></div>'
        if lo is not None and hi is not None:
            mid = t("rs.normal_range", lo=g(lo), hi=g(hi))
        elif hi is not None:
            mid = t("rs.normal_upto", hi=g(hi))
        else:
            mid = t("rs.normal_from", lo=g(lo))
        labels = f'<div class="zl"><span>{esc(t("status.low"))}</span><span>{esc(mid)}</span><span>{esc(t("status.high"))}</span></div>'
    unit = f"<small>{esc(str(r.get('unit') or ''))}</small>"
    return (f'<div class="rc {"ex" if extreme else cls}" style="animation-delay:{min(i, 10) * 0.05:.2f}s"><div class="top">'
            f'<div class="nm">{esc(str(r.get("test") or ""))}</div>{pill_html}</div>'
            f'<div class="rv">{esc(g(v)) or "—"}{unit}</div>{bar}{labels}</div>')


def order_key(r):
    s = str(r.get("status"))
    return (0 if r.get("flag") == "extreme" else 1 if s == "high" else 2 if s == "low" else 4 if s == "normal" else 3)


def hero_html(results):
    """The ring, the three coloured tiles and the split bar for a set of results."""
    bad = [r for r in results if r.get("status") in ("low", "high")]
    ok = [r for r in results if r.get("status") == "normal"]
    extreme = [r for r in results if r.get("flag") == "extreme"]
    judged = len(bad) + len(ok)
    ratio = len(ok) / judged if judged else 0
    base = "#FF5A4E" if bad else ("#22E58B" if judged else "#D5DDE2")
    ring = (f'<svg viewBox="0 0 140 140" width="170" height="170"><circle cx="70" cy="70" r="54" fill="none" stroke="{base}" stroke-width="16"/>'
            f'<circle class="arc" cx="70" cy="70" r="54" fill="none" stroke="#22E58B" stroke-width="16" stroke-linecap="round" '
            f'stroke-dasharray="{ratio * 339.3:.1f} 339.3"/></svg>')
    third = (f'<div class="tile amber"><span class="ti">🔥</span><b class="long">{esc(str(extreme[0].get("test"))[:22])}</b><span>{esc(t("rs.extreme"))}</span></div>'
             if extreme else f'<div class="tile grey"><span class="ti">🛡️</span><b>0</b><span>{esc(t("rs.no_extreme"))}</span></div>')
    pct_ok = 100 * ratio if judged else 0
    return (f'<div class="hero2"><div class="ringw">{ring}<div class="mid"><b>{len(ok)}/{judged}</b><span>{esc(t("rs.in_range"))}</span></div></div>'
            f'<div><h2>{esc(t("rs.title"))}</h2><div class="tiles">'
            f'<div class="tile red"><span class="ti">⚠️</span><b>{len(bad)}</b><span>{esc(t("rs.need"))}</span></div>'
            f'<div class="tile green"><span class="ti">✅</span><b>{len(ok)}</b><span>{esc(t("rs.normal"))}</span></div>{third}</div>'
            f'<div class="split"><i style="background:#22E58B;width:{pct_ok:.1f}%"></i><i style="background:#FF5A4E;width:{100 - pct_ok if judged else 0:.1f}%"></i></div></div></div>')
