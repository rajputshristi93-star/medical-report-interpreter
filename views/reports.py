import html
from datetime import date, timedelta

import streamlit as st

from auth import get_current_user
from database import delete_report, get_user_reports
from i18n import t
from loader import simple
from reportscss import CSS
from theme import render_footer

MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
TAG = {"high": "hi", "low": "lo", "normal": "ok"}
KNOWN = ("high", "low", "normal", "unknown", "unverified")


def esc(x):
    return html.escape("" if x is None else str(x))


def parse_day(r):
    """created_at looks like 2026-11-07T10:20:30+00:00; fall back to today if it is missing or odd."""
    try:
        return date.fromisoformat(str(r.get("created_at", ""))[:10])
    except ValueError:
        return date.today()


def nice(d):
    return f"{d.day:02d} {MON[d.month - 1].title()} {d.year}"


def title_of(r):
    return r.get("filename") or t("rp.saved")


def counts(r):
    res = r.get("results") or []
    sts = [str(x.get("status", "unknown")) for x in res]
    return len(res), sts.count("high"), sts.count("low"), sts.count("normal")


def card_head(r, d):
    n, hi, lo, ok = counts(r)
    tags = ""
    if n:
        tags = (f'<span class="rp-tag hi">{esc(t("rp.n_high", n=hi))}</span>' if hi else "") \
            + (f'<span class="rp-tag lo">{esc(t("rp.n_low", n=lo))}</span>' if lo else "") \
            + (f'<span class="rp-tag ok">{esc(t("rp.all_ok"))}</span>' if not hi and not lo else "") \
            + f'<span class="rp-tag nt">{esc(t("rp.values", n=n))}</span>'
    tg = f'<div class="rp-tg">{tags}</div>' if tags else ""
    return (f'<div class="rp-hd"><div class="rp-dt"><b>{d.day:02d}</b><span>{MON[d.month - 1]}</span></div>'
            f'<div class="rp-mid"><h3>{esc(title_of(r))}</h3><p>{esc(nice(d))} · {d.isoformat()}</p>{tg}</div></div>')


def details_html(r, d):
    res = r.get("results") or []
    h = '<div class="rp-body rp-is-open">'
    if res:
        n, hi, lo, ok = counts(r)
        h += ('<div class="rp-sum">'
              f'<div><b>{n}</b>{esc(t("rp.sum_saved"))}</div><div><b>{hi}</b>{esc(t("rp.sum_high"))}</div>'
              f'<div><b>{lo}</b>{esc(t("rp.sum_low"))}</div><div><b>{ok}</b>{esc(t("rp.sum_ok"))}</div></div>')
        rows = ""
        for x in res:
            s = str(x.get("status", "unknown"))
            cls = TAG.get(s, "un" if s == "unverified" else "nt")
            label = t(f"status.{s}") if s in KNOWN else s
            ref = " – ".join(str(v) for v in (x.get("ref_low"), x.get("ref_high")) if v is not None)
            rows += (f'<tr><td>{esc(x.get("test"))}</td><td>{esc(x.get("value"))} {esc(x.get("unit") or "")}</td>'
                     f'<td>{esc(ref)}</td><td><span class="rp-tag {cls}">{esc(label)}</span></td></tr>')
        h += (f'<div class="rp-tw"><table><thead><tr><th>{esc(t("ip.col_test"))}</th><th>{esc(t("ip.col_value"))}</th>'
              f'<th>{esc(t("ip.col_lo"))} – {esc(t("ip.col_hi"))}</th><th>{esc(t("ip.col_status"))}</th></tr></thead>'
              f'<tbody>{rows}</tbody></table></div>')
    else:
        h += f'<div class="rp-info">{esc(t("rp.no_values", date=nice(d)))}</div>'
    return h + "</div>"


# ------------------------------------------------------------------ page
st.markdown(CSS, unsafe_allow_html=True)

user = get_current_user()
signed_a, signed_b = t("rp.signed", email="\x00").split("\x00")
who = f'{esc(signed_a)}<span class="mail">{esc(user.email)}</span>{esc(signed_b)}' if user else ""
st.markdown(
    f'<div class="rp-top"><div class="ic">📁</div><div><h1>{esc(t("rp.title"))}</h1>'
    f'{f"<div class=who>{who}</div>" if who else ""}</div></div>', unsafe_allow_html=True)

if user is None:
    st.info(t("rp.login"))
    render_footer()
    st.stop()

try:
    with simple("ld.reports", "ld.reports_s", "doc"):
        reports = get_user_reports(user.id)
except Exception as e:
    print("get_user_reports error:", str(e)[:300])
    st.error(t("rp.load_err"))
    render_footer()
    st.stop()

reports = reports or []
days = {r["id"]: parse_day(r) for r in reports}

# ---- stats
latest = max(days.values()) if days else None
last30 = sum(1 for d in days.values() if d >= date.today() - timedelta(days=30))
st.markdown(
    '<div class="rp-stats">'
    f'<div class="rp-st"><div class="si">🗂️</div><div><b>{len(reports)}</b><span>{esc(t("rp.stat_total"))}</span></div></div>'
    f'<div class="rp-st"><div class="si">🆕</div><div><b>{esc(nice(latest)) if latest else "–"}</b><span>{esc(t("rp.stat_last"))}</span></div></div>'
    f'<div class="rp-st"><div class="si">📅</div><div><b>{last30}</b><span>{esc(t("rp.stat_30"))}</span></div></div></div>',
    unsafe_allow_html=True)

# ---- search + sort
SORTS = {"new": t("rp.sort_new"), "old": t("rp.sort_old"), "az": t("rp.sort_az")}
with st.container(key="rp_tools"):
    c1, c2 = st.columns([3, 1.4])
    q = c1.text_input(t("rp.search"), placeholder="🔎  " + t("rp.search"), label_visibility="collapsed", key="rp_q").strip().lower()
    sort = c2.selectbox(t("rp.sort_new"), list(SORTS), format_func=SORTS.get, label_visibility="collapsed", key="rp_sort")

shown = [r for r in reports if not q or q in f"{title_of(r)} {days[r['id']].isoformat()} {nice(days[r['id']])}".lower()]
if sort == "az":
    shown.sort(key=lambda r: title_of(r).lower())
else:
    shown.sort(key=lambda r: days[r["id"]], reverse=(sort == "new"))

if reports:
    msg = t("rp.count2", n=len(reports), order=t(f"rp.order_{sort}"))
    if len(shown) != len(reports):
        msg += " " + t("rp.showing", k=len(shown))
    st.markdown(f'<p class="rp-count">{esc(msg)}</p>', unsafe_allow_html=True)

# ---- empty states
if not reports:
    st.markdown(f'<div class="rp-empty"><div class="e">📄</div><h3>{esc(t("rp.empty_t"))}</h3><p>{esc(t("rp.empty_s"))}</p></div>', unsafe_allow_html=True)
    st.page_link("views/analyze.py", label=t("rp.go_interp"))
elif not shown:
    st.markdown(f'<div class="rp-empty"><div class="e">🔍</div><h3>{esc(t("rp.no_match_t"))}</h3><p>{esc(t("rp.no_match_s"))}</p></div>', unsafe_allow_html=True)


# ---- cards
def render_card(r):
    rid, d = str(r["id"]), days[r["id"]]
    is_open = st.session_state.get("rp_open") == rid
    with st.container(key=f"rpc-{rid}"):
        left, right = st.columns([6, 1.4], vertical_alignment="center")
        left.markdown(card_head(r, d), unsafe_allow_html=True)
        if right.button(t("rp.hide") if is_open else t("rp.view"), key=f"rptoggle_{rid}", width="stretch"):
            st.session_state["rp_open"] = None if is_open else rid
            st.session_state.pop("rp_confirm", None)
            st.rerun()
        if not is_open:
            return
        st.markdown(details_html(r, d), unsafe_allow_html=True)
        if r.get("explanation"):
            st.markdown(f'<div class="rp-expl-t">{esc(t("rs.expl_t"))}</div>', unsafe_allow_html=True)
            st.markdown(r["explanation"])
        st.markdown(f'<div class="rp-ai">{esc(t("rp.ai_note"))}</div>', unsafe_allow_html=True)
        a, b, c = st.columns([2, 3, 3], vertical_alignment="center")
        if r.get("results") and a.button(t("rp.find_doc"), key=f"rpdoc_{rid}", type="primary", width="stretch"):
            st.session_state["results"] = r["results"]  # hands this report's values to the Find a Doctor page
            st.switch_page("views/doctors.py")
        if st.session_state.get("rp_confirm") == rid:
            with c:
                st.markdown(f'<div class="rp-cf">{esc(t("rp.del_q"))}</div>', unsafe_allow_html=True)
                y, n = st.columns(2)
                if y.button(t("rp.yes_del"), key=f"rpyes_{rid}", width="stretch"):
                    try:
                        with simple("ld.delete", "ld.delete_s", "trash"):
                            delete_report(user.id, r["id"])
                        st.session_state.pop("rp_confirm", None)
                        st.session_state["rp_open"] = None
                        st.rerun()
                    except Exception as e:
                        print("delete_report error:", str(e)[:300])
                        st.error(t("rp.del_err"))
                if n.button(t("rp.cancel"), key=f"rpno_{rid}", width="stretch"):
                    st.session_state.pop("rp_confirm", None)
                    st.rerun()
        elif c.button(t("rp.del_btn"), key=f"rpdel_{rid}", width="stretch"):
            st.session_state["rp_confirm"] = rid
            st.rerun()


cur = None
for r in shown:
    d = days[r["id"]]
    if sort != "az" and (d.year, d.month) != cur:
        cur = (d.year, d.month)
        n = sum(1 for x in shown if (days[x["id"]].year, days[x["id"]].month) == cur)
        st.markdown(f'<div class="rp-month"><h2>{MONL[d.month - 1]} {d.year}</h2><span>{esc(t("rp.month_n", n=n))}</span></div>', unsafe_allow_html=True)
    render_card(r)

st.markdown(f'<div class="rp-disc"><span>⚕️</span><span>{esc(t("rp.disc"))}</span></div>', unsafe_allow_html=True)
render_footer()
