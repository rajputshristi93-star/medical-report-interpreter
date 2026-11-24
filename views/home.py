import streamlit as st

from i18n import t
from pagecss import inject_page_css
from resultcards import card_html, hero_html, order_key
from rules import add_status
from theme import render_footer

SAMPLE = [
    {"test": "Hemoglobin", "value": 10.8, "unit": "g/dL", "ref_low": 13, "ref_high": 17},
    {"test": "WBC count", "value": 7.1, "unit": "10^3/uL", "ref_low": 4, "ref_high": 10},
    {"test": "Platelets", "value": 318, "unit": "10^3/uL", "ref_low": 150, "ref_high": 410},
    {"test": "Creatinine", "value": 1.41, "unit": "mg/dL", "ref_low": 0.6, "ref_high": 1.25},
    {"test": "Sodium", "value": 139, "unit": "mmol/L", "ref_low": 137, "ref_high": 145},
    {"test": "LDL cholesterol", "value": 168, "unit": "mg/dL", "ref_low": 50, "ref_high": 130},
    {"test": "HOMA-IR (Insulin Resistance)", "value": 6.54, "unit": "score", "ref_low": 0.5, "ref_high": 1.9},
]


inject_page_css()


def rrow(name, status, width, color):
    cls = {"low": "p-low", "normal": "p-ok", "high": "p-high"}[status]
    return (f'<div class="rrow"><div class="lab"><span>{name}</span><span class="pill {cls}">{t("status." + status)}</span></div>'
            f'<div class="rbar"><i style="--w:{width}%;background:{color}"></i></div></div>')


AMBER, GREEN, RED = ("linear-gradient(90deg,#F5A623,#FFC24B)", "linear-gradient(90deg,#2FBF71,#7BE0A6)",
                     "linear-gradient(90deg,#E5484D,#FF8FA3)")
st.markdown(f"""
<div class="hero3d">
  <div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div>
  <div class="hero-copy fade-up">
    <div class="t-eyebrow">{t("hero.eyebrow")}</div>
    <div class="t-display">{t("hero.title1")}<br><span class="grad">{t("hero.title2")}</span></div>
    <p class="t-lead">{t("hero.lead")}</p>
  </div>
  <div class="report3d fade-up d2">
    <div class="ttl"><span>🧪 {t("hero.card_title")}</span><span class="t-small">{t("hero.example")}</span></div>
    {rrow(t("ex.hb"), "low", 38, AMBER)}{rrow(t("ex.wbc"), "normal", 62, GREEN)}
    {rrow(t("ex.plt"), "normal", 55, GREEN)}{rrow(t("ex.ldl"), "high", 90, RED)}
  </div>
</div>
""", unsafe_allow_html=True)

a, b, _ = st.columns([1.7, 1.4, 2.9])
with a, st.container(key="cta"):
    st.page_link("views/analyze.py", label=t("hero.cta1"), icon="🧪")
with b, st.container(key="cta2"):
    st.page_link("views/doctors.py", label=t("hero.cta2"), icon="📍")


def heading(eyebrow, title, note=""):
    st.markdown(f'<div class="t-eyebrow" style="margin-top:2.2rem">{eyebrow}</div><div class="t-h2" style="margin-top:.2rem">{title}</div>'
                + (f'<p class="t-small">{note}</p>' if note else ""), unsafe_allow_html=True)


def card(col, icon, tone, key, delay="", number=""):
    col.markdown(f'<div class="card3d {delay}"><span class="step-no">{number}</span><div class="icon3d {tone}">{icon}</div>'
                 f'<h4>{t(key + ".title")}</h4><p>{t(key + ".text")}</p></div>', unsafe_allow_html=True)


heading(t("how.eyebrow"), t("how.title"))
c = st.columns(3)
card(c[0], "📤", "", "step1", "d1", "01")
card(c[1], "🔎", "violet", "step2", "d2", "02")
card(c[2], "💡", "amber", "step3", "d3", "03")

heading(t("feat.eyebrow"), t("feat.title"))
r1, r2 = st.columns(3), st.columns(3)
card(r1[0], "🎨", "", "f1", "d1")
card(r1[1], "📊", "violet", "f2", "d2")
card(r1[2], "🗣️", "amber", "f3", "d3")
card(r2[0], "🌿", "", "f4", "d1")
card(r2[1], "📍", "rose", "f5", "d2")
card(r2[2], "🔒", "violet", "f6", "d3")

heading(t("demo.eyebrow"), t("demo.title"), t("demo.note"))
demo = add_status([dict(x) for x in SAMPLE])
st.markdown(hero_html(demo), unsafe_allow_html=True)
st.markdown('<div class="rcg">' + "".join(card_html(r, i) for i, r in enumerate(sorted(demo, key=order_key)[:4])) + "</div>", unsafe_allow_html=True)

st.markdown(f'<div class="t-h2">{t("faq.title")}</div>', unsafe_allow_html=True)
for n in range(1, 5):
    with st.expander(t(f"faq{n}.q")):
        st.write(t(f"faq{n}.a"))
render_footer()
