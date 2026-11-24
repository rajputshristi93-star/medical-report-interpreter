"""Find a doctor: which kind of specialist fits the report, search links near the patient, and the verified
directory (Supabase table 'doctors') that you maintain. It never recommends a person on its own, and the typed
location is not stored."""
import html
import re
from urllib.parse import quote_plus

ORDER = {"urgent": 0, "attention": 1, "note": 2}
esc = html.escape

# key -> (English name, search terms, English reason, icon, colour). Shown text comes from i18n (sp.<key>.name / .why).
SPEC = {
    "general": ("General Physician (family doctor)", ["general physician"], "A good first stop.", "👨‍⚕️", "#D6F5EE"),
    "diabetes": ("Diabetologist or Endocrinologist", ["diabetologist", "endocrinologist"], "Blood sugar and diabetes.", "🩸", "#E6DFFF"),
    "nephro": ("Nephrologist (kidney specialist)", ["nephrologist"], "Kidney function.", "💧", "#DCEBFF"),
    "endocrine": ("Endocrinologist (thyroid and hormone specialist)", ["endocrinologist"], "Thyroid and hormones.", "🦋", "#FFE3F1"),
    "gastro": ("Gastroenterologist or Hepatologist (liver specialist)", ["gastroenterologist", "hepatologist"], "Liver.", "🍽️", "#FFEBCF"),
    "cardio": ("Cardiologist (heart specialist)", ["cardiologist"], "Heart risk.", "❤️", "#FFDCDC"),
    "haem": ("Hematologist (blood specialist)", ["hematologist"], "Blood counts.", "🔬", "#DDF3FF"),
    "rheum": ("Rheumatologist (joint and gout specialist)", ["rheumatologist"], "Gout and joints.", "🦴", "#F1E9DC"),
    "nutrition": ("Dietitian or General Physician", ["dietitian", "general physician"], "Vitamins and iron.", "🥗", "#E1F6D9"),
}

# Pattern title (lower case) -> specialty. First match wins.
RULES = [
    (r"blood sugar|glucose", "diabetes"), (r"kidney", "nephro"), (r"thyroid", "endocrine"),
    (r"liver|bile|bilirubin", "gastro"), (r"cholesterol|triglyceride", "cardio"),
    (r"hemoglobin|white blood|platelet", "haem"), (r"uric", "rheum"), (r"vitamin|ferritin", "nutrition"),
    (r"albumin|inflammation|sodium|potassium|calcium", "general"),
]
TIP_ICONS = ["🪪", "⭐", "💬", "📄"]
TIP_COLORS = ["#DFF7F0", "#FFF3D6", "#E3EDFF", "#EFE6FF"]


def maps_url(query):
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def web_url(query):
    return "https://www.google.com/search?q=" + quote_plus(query)


def safe_url(u):
    u = str(u or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else None


def suggest(results, age=None, sex=None):
    """Returns {'urgent': [...patterns], 'items': [{key, level, reasons}], 'patterns': [...]}."""
    from conditions import find_patterns
    patterns = find_patterns(results, age, sex)
    groups = {}
    for p in patterns:
        title = p["title"].lower()
        for rx, key in RULES:
            if re.search(rx, title):
                g = groups.setdefault(key, {"key": key, "level": p["level"], "reasons": []})
                g["reasons"].append(p["title"])
                if ORDER[p["level"]] < ORDER[g["level"]]:
                    g["level"] = p["level"]
                break
    items = sorted(groups.values(), key=lambda g: (ORDER[g["level"]], g["key"]))
    return {"urgent": [p for p in patterns if p["level"] == "urgent"], "items": items, "patterns": patterns}


def city_doctors(city, limit=600):
    """Doctors from the verified 'doctors' table for this place. Returns [] if the table is missing."""
    words = re.findall(r"[A-Za-z]{3,}", city or "")  # 'Pune 411001' -> ['Pune']
    if not words:
        return []
    try:
        from supabase_client import get_supabase
        return (get_supabase().table("doctors").select("*").ilike("city", f"%{max(words, key=len)}%")
                .limit(limit).execute().data or [])
    except Exception as e:
        print("doctors table not available:", str(e)[:120])
        return []


def curated(terms, city):  # kept for older code
    return [r for r in city_doctors(city) if any(t in str(r.get("specialty", "")).lower() for t in terms)]


# ---------------------------------------------------------------- html pieces
def links_html(terms, loc, seen):
    from i18n import t
    out = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        q = f"{term} near {loc}" if loc else term
        if loc:
            out.append(f'<a class="lb pri" href="{esc(maps_url(q))}" target="_blank" rel="noopener">🗺️ {esc(t("dr.maps"))} {esc(term)}</a>'
                       f'<a class="lb" href="{esc(web_url(q + " doctor"))}" target="_blank" rel="noopener">🔎 {esc(t("dr.search"))} {esc(term)}</a>')
        else:
            out.append(f'<span class="lb off">🗺️ {esc(t("dr.maps"))} {esc(term)}</span><span class="lb off">🔎 {esc(t("dr.search"))} {esc(term)}</span>')
    return '<div class="lbs">' + "".join(out) + "</div>" if out else ""


def doc_card(d):
    from i18n import t
    name = str(d.get("name") or "")
    plain = re.sub(r"^(dr|prof)\.?\s+", "", name, flags=re.I)
    initials = "".join(w[0] for w in plain.split()[:2]).upper() or "Dr"
    shown = name if re.match(r"^(dr|prof)\.?\s", name, flags=re.I) else f"Dr. {name}"
    meta = " · ".join(x for x in (d.get("clinic"),) if x)
    chips = ""
    if d.get("address"):
        chips += f'<div class="dchip">📍 {esc(str(d["address"]))}{", " + esc(str(d["city"])) if d.get("city") else ""}</div>'
    phone = re.sub(r"[^0-9+\-\s()]", "", str(d.get("phone") or "")).strip()
    if phone:
        chips += f'<div class="dchip tel">📞 {esc(phone)}</div>'
    btns = ""
    if phone:
        btns += f'<a class="lb pri" href="tel:{esc(phone.replace(" ", ""))}">📞 {esc(t("dr.call"))}</a>'
    for label, field, icon in (("dr.website", "website", "🌐"), ("dr.profile", "social_url", "👤"), ("dr.source", "source_url", "📎")):
        u = safe_url(d.get(field))
        if u:
            btns += f'<a class="lb" href="{esc(u)}" target="_blank" rel="noopener">{icon} {esc(t(label))}</a>'
    return (f'<div class="doc"><div class="dmain"><div class="av">{esc(initials)}</div><div><div class="dn">{esc(shown)}</div>'
            f'<span class="dsp">{esc(str(d.get("specialty") or ""))}</span><div class="dq">{esc(str(d.get("qualification") or ""))}</div>'
            f'<div class="dm">{esc(meta)}</div></div></div><div class="dchips">{chips}</div><div class="dbtn">{btns}</div>'
            f'<div class="dfoot">{esc(t("dr.checked", date=str(d.get("verified_on") or "-")))}</div></div>')


def group_of(d, groups):
    spec = str(d.get("specialty", "")).lower()
    for key, terms in groups:
        if any(term in spec for term in terms):
            return key
    return None


# ---------------------------------------------------------------- page
def render_doctor_page():
    import streamlit as st
    from i18n import localize, t
    from pagecss import inject_page_css
    from theme import render_footer

    inject_page_css()
    st.markdown(f'<div class="dr-top"><div class="pic">🩺</div><div><h1>{esc(t("dr.title"))}</h1><p>{esc(t("dr.sub"))}</p></div></div>'
                f'<div class="nc no" style="margin-bottom:1rem"><div class="ni">⚠️</div><div><p>{esc(t("dr.warn"))}</p></div></div>',
                unsafe_allow_html=True)

    with st.container(key="dcard"):
        c1, c2, c3 = st.columns([2, 1, 1])
        loc = c1.text_input(f"{t('dr.city')} {t('dr.city_note')}", key="doc_loc", placeholder="📍  " + t("dr.city_ph")).strip()
        age = c2.number_input(f"{t('dr.age')} {t('dr.opt')}", min_value=0, max_value=120, value=None, step=1, key="doc_age", placeholder="e.g. 45")
        sex = c3.selectbox(f"{t('dr.sex')} {t('dr.opt')}", ["Select", "Female", "Male"], key="doc_sex",
                           format_func=lambda k: {"Select": t("dr.select"), "Female": t("ip.sex_f"), "Male": t("ip.sex_m")}[k])
        st.markdown(f'<div class="t-small">🔒 {esc(t("dr.loc_note"))}</div>', unsafe_allow_html=True)
        if loc:
            st.markdown(f'<div class="dr-ok">✓ {esc(t("dr.on", loc=loc))} {esc(t("dr.on_docs"))}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="dr-hint">{esc(t("dr.need_loc"))}</div>', unsafe_allow_html=True)

    results = st.session_state.get("results")
    seen, groups_for_docs = set(), []
    if results:
        s = suggest(results, age if age and age >= 18 else None, sex if sex != "Select" else None)
        flagged = [r for r in results if r.get("status") in ("low", "high")]
        chips = "".join(f'<span class="fc">{esc(str(r.get("test")))} · {"↑" if r["status"] == "high" else "↓"} {esc(t("status." + r["status"]))}</span>'
                        for r in flagged[:10])
        st.markdown(f'<div class="dr-rep"><b>✅ {esc(t("dr.rep_based"))}</b><div class="fcs">{chips}</div></div>', unsafe_allow_html=True)
        if s["urgent"]:
            P = localize([p["title"] for p in s["urgent"]])
            st.markdown(f'<div class="alertb"><span class="pulse">🚨</span><div><b>{esc(t("dr.urgent"))}</b> '
                        f'{esc(", ".join(P[p["title"]] for p in s["urgent"]))}. {esc(t("dr.urgent2"))}'
                        f'{links_html(["emergency hospital"], loc, set())}</div></div>', unsafe_allow_html=True)
        keys = ["general"] + [g["key"] for g in s["items"] if g["key"] != "general"]
        reasons = {g["key"]: g["reasons"] for g in s["items"]}
        R = localize([x for v in reasons.values() for x in v])
        docs_all = city_doctors(loc) if loc else []
        st.markdown(f'<div class="sec-t" style="margin-top:1rem">{esc(t("dr.based"))} <span class="exp" style="background:#D9F5EE;color:#0B7A6B">🔗 {esc(t("dr.from"))}</span></div>',
                    unsafe_allow_html=True)
        if not s["items"]:
            st.info(t("dr.none"))
        cards = ""
        for key in keys:
            _name, terms, _why, icon, color = SPEC[key]
            groups_for_docs.append((key, terms))
            because = "".join(f'<span class="fc red">{esc(R[x])}</span>' for x in reasons.get(key, []))
            n_here = sum(1 for d in docs_all if any(term in str(d.get("specialty", "")).lower() for term in terms)) if loc else 0
            near = f'<div class="near">👥 {esc(t("dr.near", n=n_here, loc=loc))}</div>' if loc and n_here else ""
            cards += (f'<div class="spc"><div class="sph"><div class="spi" style="background:{color}">{icon}</div><h3>{esc(t(f"sp.{key}.name"))}</h3></div>'
                      f'<p>{esc(t(f"sp.{key}.why"))}</p>' + (f'<div class="bc"><span class="t-small">{esc(t("dr.because"))}</span>{because}</div>' if because else "")
                      + near + links_html(terms, loc, seen) + "</div>")
        st.markdown(f'<div class="spg">{cards}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="dr-note"><span class="ni">📄</span><div>{esc(t("dr.pre"))}</div></div>', unsafe_allow_html=True)
        with st.container(key="cta2"):
            st.page_link("views/analyze.py", label=t("dr.pre_cta") + "  →", icon="🧪")
        with st.container(key="rcard"):
            key = st.selectbox(t("dr.specialty"), list(SPEC), key="doc_spec", format_func=lambda k: t(f"sp.{k}.name"))
            _name, terms, _why, icon, color = SPEC[key]
            groups_for_docs.append((key, terms))
            st.markdown(f'<div class="spc plain"><div class="sph"><div class="spi" style="background:{color}">{icon}</div><h3>{esc(t(f"sp.{key}.name"))}</h3></div>'
                        f'<p>{esc(t(f"sp.{key}.why"))}</p>{links_html(terms, loc, seen)}</div>', unsafe_allow_html=True)
            if not loc:
                st.caption(t("dr.enter_loc"))
        docs_all = city_doctors(loc) if loc else []

    if loc:
        shown = [(d, group_of(d, groups_for_docs)) for d in docs_all]
        shown = [(d, g) for d, g in shown if g]
        st.markdown(f'<div class="sec-t" style="margin-top:1.4rem">{esc(t("dr.sugg"))} <span class="exp" style="background:#D9F5EE;color:#0B7A6B">'
                    f'{esc(t("dr.count", n=len(shown)))}</span></div>', unsafe_allow_html=True)
        if not shown:
            st.info(t("dr.no_docs"))
        else:
            counts = {k: sum(1 for _d, g in shown if g == k) for k, _ in groups_for_docs}
            options = ["all"] + [k for k, _ in groups_for_docs if counts[k]]
            sel = st.segmented_control("dg", options, default="all", key="dr_group", label_visibility="collapsed",
                                       format_func=lambda k: (f"{t('dr.all')} · {len(shown)}" if k == "all"
                                                              else f"{t(f'sp.{k}.name').split(' (')[0]} · {counts[k]}")) or "all"
            q = st.text_input("find", key="dr_q", placeholder="🔎  " + t("dr.find_ph"), label_visibility="collapsed").strip().lower()
            rows = [d for d, g in shown if (sel == "all" or g == sel)
                    and (not q or q in (str(d.get("name", "")) + " " + str(d.get("clinic", "")) + " " + str(d.get("address", ""))).lower())]
            n = st.session_state.setdefault("dr_n", 6)
            st.caption(t("dr.showing", a=min(n, len(rows)), b=len(rows)))
            st.markdown("".join(doc_card(d) for d in rows[:n]), unsafe_allow_html=True)
            if len(rows) > n and st.button(t("dr.more"), key="dr_more"):
                st.session_state["dr_n"] = n + 6
                st.rerun()
    elif results:
        st.caption(t("dr.enter_loc"))

    tips = "".join(f'<div class="tip" style="background:{TIP_COLORS[i]}"><span class="ni">{TIP_ICONS[i]}</span><p>{esc(t(f"dr.tip{i + 1}"))}</p></div>' for i in range(4))
    st.markdown(f'<div class="sec-t" style="margin-top:1.6rem">{esc(t("dr.how"))}</div><div class="tipg">{tips}</div>', unsafe_allow_html=True)
    render_footer()


def render_doctor_hint():
    """Kept for older code: a small pointer. The new Interpreter page has its own 'Who to see' tab."""
    import streamlit as st
    from i18n import t

    if st.session_state.get("results"):
        st.page_link("views/doctors.py", label=t("rs.who_cta"), icon="📍")
