import hashlib
import html
import io
from datetime import date

import pandas as pd
import streamlit as st

from advice import render_advice_section
from auth import get_current_user
from charts import render_report_charts
from conditions import render_patterns_section
from database import save_report
from doctor_finder import suggest
from extractor import extract_text, looks_scanned
from i18n import t
from loader import celebrate, pop_cancelled, run_cancellable
from interpreter import (
    explain_results,
    extract_results,
    extract_results_from_file,
    find_unread_lines,
    verify_against_text,
)
from ml_risk import render_ml_section
from pagecss import inject_page_css
from resultcards import card_html, hero_html, order_key
from rules import add_status
from theme import render_footer

MAX_MB = 10
MAX_BYTES = MAX_MB * 1024 * 1024
esc = html.escape

COMMON_TESTS = [
    "Hemoglobin", "Hematocrit", "RBC Count", "WBC Count", "Platelet Count", "MCV", "MCH", "MCHC", "RDW",
    "Neutrophils", "Lymphocytes", "ESR", "CRP", "Fasting Blood Sugar", "HbA1c", "Total Cholesterol",
    "LDL Cholesterol", "HDL Cholesterol", "Triglycerides", "Creatinine", "Blood Urea", "BUN", "eGFR",
    "Uric Acid", "Sodium", "Potassium", "Calcium", "ALT (SGPT)", "AST (SGOT)", "ALP", "Total Bilirubin",
    "Albumin", "Total Protein", "TSH", "Free T4", "Free T3", "Vitamin D", "Vitamin B12", "Ferritin",
    "Iron", "TIBC",
]
SEX_OPTIONS = ["Prefer not to say", "Female", "Male", "Other"]
SEX_KEYS = {"Prefer not to say": "ip.sex_none", "Female": "ip.sex_f", "Male": "ip.sex_m", "Other": "ip.sex_o"}


# ---------------------------------------------------------------- helpers
def get_mime(filename):
    name = filename.lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def parse_num(s):
    """Returns (number or None, ok). Blank is valid and gives (None, True)."""
    s = str(s or "").strip().replace(",", "")
    if not s:
        return None, True
    try:
        return float(s), True
    except ValueError:
        return None, False


def build_context(age, sex, notes):
    parts = []
    if age:
        parts.append(f"Age: {int(age)} years")
    if sex and sex != "Prefer not to say":
        parts.append(f"Sex: {sex}")
    if notes and notes.strip():
        parts.append(f"Notes: {notes.strip()[:300]}")
    return "\n".join(parts)


def explain(results, context):
    lang = st.session_state.get("lang_ai", "English")
    try:
        return explain_results(results, context, lang)  # the explanation is written in the chosen language
    except TypeError:
        return explain_results(results, context)  # older interpreter.py without the language option


# ---------------------------------------------------------------- processing
def file_steps():
    return [(t("ld.read"), t("ld.read_s"), 18, "doc"), (t("ld.find"), t("ld.find_s"), 40, "search"),
            (t("ld.check"), t("ld.check_s"), 62, "shield"), (t("ld.write"), t("ld.write_s"), 82, "pen"),
            (t("ld.ready"), t("ld.ready_s"), 96, "chart")]


def manual_steps():
    return [(t("ld.m_check"), t("ld.m_check_s"), 25, "shield"), (t("ld.write"), t("ld.write_s"), 70, "pen"),
            (t("ld.ready"), t("ld.ready_s"), 95, "chart")]


def explain(results, context, lang):
    try:
        return explain_results(results, context, lang)  # the explanation is written in the chosen language
    except TypeError:
        return explain_results(results, context)  # older interpreter.py without the language option


def process_file(data, name, progress):
    """Runs in the background (no st.* calls here). Returns (results, source, unread)."""
    progress(1)
    mime = get_mime(name)
    text, unread = "", []
    from_file = mime != "application/pdf"  # images always go straight to the AI
    if not from_file:
        text = extract_text(io.BytesIO(data))
        from_file = looks_scanned(text)  # scanned PDF: no text layer
    progress(2)
    if from_file:
        results = extract_results_from_file(data, mime)
        progress(3)
    else:
        try:
            results = extract_results(text, progress=lambda f: progress(2, f))  # real progress while the chunks are read
        except TypeError:
            results = extract_results(text)  # older interpreter.py
        progress(3)
        unread = find_unread_lines(results, text)
        results = verify_against_text(results, text)
    return add_status(results), ("image" if from_file else "text"), unread


def handle(status, value, error_key="ip.err_gen"):
    """Shows an error, or keeps the results in this browser session only and reloads the page. Nothing is saved."""
    if status == "error":
        print("pipeline error:", repr(value)[:300])
        st.error(t("ip.err_busy") if isinstance(value, RuntimeError) else t(error_key))
        return
    results, source, unread, explanation = value
    if not results:
        st.error(t("ip.err_none"))
        return
    st.session_state.update({"results": results, "explanation": explanation, "source": source, "unread": unread})
    for k in ("rs_tab", "rs_flt", "saved_for"):
        st.session_state.pop(k, None)
    st.rerun()


def run_upload(file, context):
    if file is None:
        st.warning(t("ip.err_nofile"))
        return
    if file.size > MAX_BYTES:
        st.error(t("ip.err_big", mb=MAX_MB))
        return
    data, name = file.getvalue(), file.name
    lang = st.session_state.get("lang_ai", "English")

    def work(progress):
        results, source, unread = process_file(data, name, progress)
        if not results:
            return results, source, unread, ""
        progress(4)
        explanation = explain(results, context, lang)
        progress(5)
        return results, source, unread, explanation

    handle(*run_cancellable(file_steps(), work))


def run_manual(rows, context):
    lang = st.session_state.get("lang_ai", "English")

    def work(progress):
        progress(1)
        checked = add_status(rows)
        progress(2)
        explanation = explain(checked, context, lang)
        progress(3)
        return checked, "manual", [], explanation

    handle(*run_cancellable(manual_steps(), work), error_key="ip.err_manual_gen")


# ---------------------------------------------------------------- manual entry
def manual_form():
    if "row_ids" not in st.session_state:
        st.session_state["row_ids"] = [0]
        st.session_state["next_id"] = 1
    ids = st.session_state["row_ids"]
    widths = [3.2, 1.2, 1.2, 1.2, 1.2, 0.6]
    st.markdown(f'<div class="sec-t">{esc(t("ip.m_t"))}</div>', unsafe_allow_html=True)
    head = st.columns(widths)
    for col, key in zip(head, ["ip.col_test", "ip.col_value", "ip.col_unit", "ip.col_lo", "ip.col_hi", ""]):
        col.caption(t(key) if key else "")
    for i in list(ids):
        c = st.columns(widths)
        c[0].selectbox("Test", COMMON_TESTS, index=None, accept_new_options=True, placeholder=t("ip.test_ph"),
                       key=f"t_{i}", label_visibility="collapsed")
        c[1].text_input("Value", key=f"v_{i}", placeholder=t("ip.val_ph"), label_visibility="collapsed")
        c[2].text_input("Unit", key=f"u_{i}", placeholder=t("ip.unit_ph"), label_visibility="collapsed")
        c[3].text_input("Ref low", key=f"lo_{i}", placeholder=t("ip.lo_ph"), label_visibility="collapsed")
        c[4].text_input("Ref high", key=f"hi_{i}", placeholder=t("ip.hi_ph"), label_visibility="collapsed")
        if c[5].button("✕", key=f"del_{i}") and len(ids) > 1:
            ids.remove(i)
            st.rerun()
    if st.button("＋ " + t("ip.add_row"), key="add_row"):
        ids.append(st.session_state["next_id"])
        st.session_state["next_id"] += 1
        st.rerun()
    st.caption(t("ip.tip"))


def collect_manual():
    results, problems = [], []
    for n, i in enumerate(st.session_state["row_ids"], start=1):
        name = str(st.session_state.get(f"t_{i}") or "").strip()
        raw_value = str(st.session_state.get(f"v_{i}") or "").strip()
        if not name and not raw_value:
            continue
        value, ok_v = parse_num(raw_value)
        lo, ok_lo = parse_num(st.session_state.get(f"lo_{i}"))
        hi, ok_hi = parse_num(st.session_state.get(f"hi_{i}"))
        if not name or value is None or not (ok_v and ok_lo and ok_hi):
            problems.append(t("ip.err_row", n=n))
            continue
        results.append({"test": name, "value": value, "unit": str(st.session_state.get(f"u_{i}") or "").strip(),
                        "ref_low": lo, "ref_high": hi, "verified": None})
    return results, problems


# ---------------------------------------------------------------- input screen
def input_screen():
    if pop_cancelled():
        st.info(t("ld.cancelled"))
    st.markdown(f"""
<div class="ip-head"><h1>{esc(t("ip.title"))}</h1><p>{esc(t("ip.lead"))}</p></div>
<div class="ip-badges"><span>📄 {esc(t("ip.badge1"))}</span><span>🔒 {esc(t("ip.badge2"))}</span><span>✅ {esc(t("ip.badge3"))}</span><span>🎨 {esc(t("ip.badge4"))}</span><span>💾 {esc(t("ip.badge5"))}</span></div>
<div class="nc info"><div class="ni">⚕️</div><div><strong>{esc(t("ip.disc_t"))}</strong><p>{esc(t("ip.disc"))}</p></div></div>
<div class="ncg">
<div class="nc ok"><div class="ni">✅</div><div><strong>{esc(t("ip.sup_t"))}</strong><p>{esc(t("ip.sup"))}</p></div></div>
<div class="nc no"><div class="ni">🚫</div><div><strong>{esc(t("ip.nosup_t"))}</strong><p>{esc(t("ip.nosup"))}</p></div></div>
</div>""", unsafe_allow_html=True)

    with st.container(key="pcard"):
        st.markdown(f'<div class="card-head"><div class="pic">🧑‍⚕️</div><div><h2>{esc(t("ip.pat_t"))}</h2><p>{esc(t("ip.pat_s"))}</p></div>'
                    f'<span class="opt">{esc(t("ip.optional"))}</span></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        age = c1.number_input(t("ip.age"), min_value=0, max_value=120, value=None, step=1, placeholder=t("ip.age_ph"), key="ip_age")
        sex = c2.selectbox(t("ip.sex"), SEX_OPTIONS, format_func=lambda k: t(SEX_KEYS[k]), key="ip_sex")
        notes = st.text_input(t("ip.notes"), placeholder=t("ip.notes_ph"), max_chars=200, key="ip_notes")
        st.markdown(f'<div class="pnote">🔒 <span>{esc(t("ip.pat_note"))}</span></div>', unsafe_allow_html=True)
    context = build_context(age, sex, notes)

    mode = st.session_state.setdefault("ip_mode", "m")
    with st.container(key="fcard"):
        st.markdown(f'<div class="sec-t" style="margin-top:.4rem">{esc(t("ip.choose"))}</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for col, code in zip(cols, ("m", "p", "i")):
            with col, st.container(key=f"fmt_{code}" + ("_on" if mode == code else "")):
                if st.button(t(f"ip.fmt_{code}"), key=f"fmtbtn_{code}", use_container_width=True):
                    st.session_state["ip_mode"] = code
                    st.rerun()
        st.write("")
        file = None
        if mode == "m":
            manual_form()
        else:
            kind = "pdf" if mode == "p" else "img"
            st.markdown(f'<div class="sec-t">{esc(t("ip.p_t" if mode == "p" else "ip.i_t"))}</div>', unsafe_allow_html=True)
            with st.container(key="dz"):
                file = st.file_uploader("file", type=["pdf"] if mode == "p" else ["png", "jpg", "jpeg"],
                                        key=f"up_{kind}", label_visibility="collapsed")
            st.markdown(f'<div class="dz-sub">{esc(t("ip.drop_s_" + kind))}</div><div class="dz-lim">{esc(t("ip.drop_l_" + kind))}</div>',
                        unsafe_allow_html=True)
            if file is not None:
                st.caption(t("ip.sel_file", name=file.name, size=f"{file.size / (1024 * 1024):.2f}", mb=MAX_MB))
        with st.container(key="go_cta"):
            go = st.button(t("ip.go"), type="primary", key="go", use_container_width=True)

    if go:
        if mode == "m":
            manual_results, problems = collect_manual()
            for p in problems:
                st.warning(p)
            if not manual_results:
                st.error(t("ip.err_manual"))
            else:
                run_manual(manual_results, context)
        else:
            run_upload(file, context)


# ---------------------------------------------------------------- results screen
def head(icon, title, sub=""):
    st.markdown(f'<div class="rc-head"><div class="ic">{icon}</div><div><h3>{esc(title)}</h3>'
                + (f'<p class="t-small" style="margin:0">{esc(sub)}</p>' if sub else "") + '</div></div>', unsafe_allow_html=True)


def save_card(results):
    user = get_current_user()
    fp = hashlib.sha1(str(results).encode("utf-8")).hexdigest()
    if st.session_state.get("saved_for") == fp:
        st.success(t("sv.ok"))
        return
    st.caption(t("sv.about"))
    title = st.text_input(t("sv.title"), value=t("sv.default", date=f"{date.today():%d %b %Y}"), key="save_title", max_chars=80)
    agree = st.checkbox(t("sv.agree"), key="save_agree")
    if st.button(t("sv.btn"), type="primary", key="save_btn", disabled=not agree or user is None):
        try:
            save_report(user_id=user.id, filename=title.strip() or "Untitled report",
                        source=st.session_state.get("source", "text"), context=None, results=results,
                        explanation=st.session_state.get("explanation", ""), confirmed=True)
            st.session_state["saved_for"] = fp
            celebrate(t("sv.done"), t("sv.done_s"))
            st.rerun()
        except Exception as e:
            print("save_report error:", str(e)[:300])
            st.error(t("sv.err"))


def results_screen():
    results = st.session_state["results"]
    source = st.session_state.get("source", "text")
    bad = [r for r in results if r.get("status") in ("low", "high")]
    ok = [r for r in results if r.get("status") == "normal"]
    extreme = [r for r in results if r.get("flag") == "extreme"]
    judged = len(bad) + len(ok)

    top = st.columns([4, 1.3], vertical_alignment="center")
    top[0].markdown(f'<div class="okb"><i>✓</i>{esc(t("rs.success"))}</div>', unsafe_allow_html=True)
    if top[1].button(t("rs.new"), key="rs_new", use_container_width=True):
        for k in ("results", "explanation", "source", "unread", "saved_for", "rs_tab", "rs_flt"):
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown(hero_html(results), unsafe_allow_html=True)
    if extreme:
        st.markdown(f'<div class="alertb"><span class="pulse">⚠️</span><div>{esc(t("rs.alert"))}</div></div>', unsafe_allow_html=True)

    tabs = [("results", "📋", "rs.tab_results"), ("plain", "💬", "rs.tab_plain"), ("habits", "🌿", "rs.tab_habits"),
            ("who", "🩺", "rs.tab_who"), ("patterns", "🔎", "rs.tab_patterns"), ("save", "💾", "rs.tab_save"),
            ("screen", "🧠", "rs.tab_screen")]
    tab = st.session_state.setdefault("rs_tab", "results")
    rail, main = st.columns([1, 3.2])
    with rail, st.container(key="rail"):
        for n, (code, icon, key) in enumerate(tabs, start=1):
            with st.container(key=f"rail_{n}" + ("_on" if tab == code else "")):
                if st.button(f"{icon}  {t(key)}", key=f"railbtn_{code}", use_container_width=True):
                    st.session_state["rs_tab"] = code
                    st.rerun()

    with main:
        if tab == "results":
            with st.container(key="rcard"):
                head("📋", t("rs.title"))
                if source == "image":
                    st.info(t("rs.src_image"))
                elif source == "manual":
                    st.info(t("rs.src_manual"))
                if any(r.get("verified") is False for r in results):
                    st.warning(t("rs.unverified"))
                counts = {"all": len(results), "high": sum(r.get("status") == "high" for r in results),
                          "low": sum(r.get("status") == "low" for r in results), "normal": len(ok)}
                options = [k for k in ("all", "high", "low", "normal") if k == "all" or counts[k]]
                flt = st.segmented_control("filter", options, default="all", key="rs_flt", label_visibility="collapsed",
                                           format_func=lambda k: f"{t('rs.f_all') if k == 'all' else t('status.' + k)} · {counts[k]}") or "all"
                shown = sorted([r for r in results if flt == "all" or r.get("status") == flt], key=order_key)
                if shown:
                    st.markdown('<div class="rcg">' + "".join(card_html(r, i) for i, r in enumerate(shown)) + "</div>", unsafe_allow_html=True)
                else:
                    st.info(t("rs.none_shown"))
                if flt in ("high", "low") and ok:
                    st.markdown(f'<div class="okbx">✓ {esc(t("rs.others", n=len(ok)))}</div>', unsafe_allow_html=True)
                unread = st.session_state.get("unread", [])
                if unread:
                    with st.expander("⚠️ " + t("rs.unread", n=len(unread))):
                        st.write(t("rs.unread_help"))
                        for line in unread:
                            st.text(line)
                st.caption(t("rs.not_saved"))
            render_report_charts(results)
        elif tab == "plain":
            with st.container(key="rcard"):
                head("💬", t("rs.expl_t"))
                st.markdown(st.session_state.get("explanation", ""))
                st.caption(t("rs.mistakes"))
        elif tab == "habits":
            with st.container(key="rcard"):
                head("🌿", t("rs.tab_habits"))
                render_advice_section(embedded=True)
        elif tab == "who":
            sug = suggest(results)
            keys = ["general"] + [x["key"] for x in sug["items"] if x["key"] != "general"]
            pills = "".join(f"<span>{esc(t(f'sp.{k}.name').split(' (')[0])}</span>" for k in dict.fromkeys(keys))
            st.markdown(f'<div class="who"><h3>🩺 {esc(t("rs.who_t"))}</h3><p>{esc(t("rs.who_lead"))}</p><div class="pills">{pills}</div></div>',
                        unsafe_allow_html=True)
            with st.container(key="who_cta"):
                st.page_link("views/doctors.py", label=t("rs.who_cta"), icon="📍")
        elif tab == "patterns":
            with st.container(key="rcard"):
                head("🔎", t("rs.tab_patterns"))
                render_patterns_section(embedded=True)
        elif tab == "save":
            with st.container(key="rcard"):
                head("💾", t("sv.btn"))
                save_card(results)
        else:
            with st.container(key="rcard"):
                head("🧠", t("rs.tab_screen"))
                render_ml_section(embedded=True)


inject_page_css()
if "results" in st.session_state:
    results_screen()
else:
    input_screen()
render_footer()
