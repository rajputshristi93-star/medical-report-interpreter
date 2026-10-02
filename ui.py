import streamlit as st

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1100px;}
footer {visibility: hidden;}
.hero {background: linear-gradient(135deg, #0F9D8A 0%, #1B6FB5 100%); color: #fff; padding: 48px 40px; border-radius: 24px; margin-bottom: 20px;}
.hero-grid {display: grid; grid-template-columns: 1.2fr 1fr; gap: 28px; align-items: center;}
@media (max-width: 800px) {.hero-grid {grid-template-columns: 1fr;} .hero {padding: 32px 22px;}}
.hero h1 {font-size: 2.5rem; line-height: 1.15; margin: 0 0 12px 0; color: #fff !important;}
.hero .lead {font-size: 1.1rem; margin: 0; color: #fff !important; opacity: .95;}
.pill {display: inline-block; background: rgba(255,255,255,.2); padding: 6px 14px; border-radius: 999px; font-size: .85rem; margin-bottom: 16px; color: #fff;}
.demo {background: #fff; border-radius: 16px; padding: 18px; color: #12313A;}
.demo b {color: #12313A;}
.demo table {width: 100%; border-collapse: collapse; margin-top: 8px;}
.demo td {padding: 8px 6px; border-bottom: 1px solid #EEF4F3; font-size: .95rem; color: #12313A;}
.demo .note {margin: 10px 0 0 0; color: #4A6670; font-size: .85rem;}
.badge {padding: 3px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600;}
.b-low {background: #FFF3CD; color: #856404;}
.b-high {background: #F8D7DA; color: #721C24;}
.b-normal {background: #D4EDDA; color: #155724;}
.grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 12px 0 28px 0;}
.card {background: #fff; border: 1px solid #E3EEEC; border-radius: 16px; padding: 20px; box-shadow: 0 2px 10px rgba(15,157,138,.06);}
.card h4 {margin: 0 0 6px 0; color: #12313A;}
.card p {margin: 0; color: #4A6670; font-size: .95rem;}
.step-num {display: inline-flex; width: 34px; height: 34px; align-items: center; justify-content: center; border-radius: 50%; background: #0F9D8A; color: #fff; font-weight: 700; margin-bottom: 10px;}
.section-title {font-size: 1.6rem; font-weight: 700; color: #12313A; margin: 28px 0 4px 0;}
.section-sub {color: #4A6670; margin: 0 0 12px 0;}
.disclaimer {background: #FFF8E6; border: 1px solid #F5E1A4; color: #6B5300; padding: 10px 14px; border-radius: 12px; font-size: .9rem; margin-bottom: 10px;}
.footer {margin-top: 40px; padding: 24px 0; border-top: 1px solid #E3EEEC; color: #4A6670; font-size: .88rem;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def disclaimer():
    st.markdown(
        '<div class="disclaimer">⚕️ For information only. This tool does not diagnose or give medical advice. '
        'Always discuss your results with a doctor.</div>',
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        '<div class="footer">⚕️ <b>Medical disclaimer:</b> this app is for information only and does not provide '
        'medical advice, diagnosis, or treatment. It can make mistakes, so always check values against your '
        'original report and consult a qualified doctor.</div>',
        unsafe_allow_html=True,
    )