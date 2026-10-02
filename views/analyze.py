import io

import pandas as pd
import streamlit as st

from extractor import extract_text, looks_scanned
from interpreter import (
    explain_results,
    extract_results,
    extract_results_from_file,
    find_unread_lines,
    verify_against_text,
)
from rules import add_status
from ui import footer

MAX_MB = 10

COMMON_TESTS = [
    "Hemoglobin", "Hematocrit", "RBC Count", "WBC Count", "Platelet Count", "MCV", "MCH", "MCHC", "RDW",
    "Neutrophils", "Lymphocytes", "ESR", "CRP", "Fasting Blood Sugar", "HbA1c", "Total Cholesterol",
    "LDL Cholesterol", "HDL Cholesterol", "Triglycerides", "Creatinine", "Blood Urea", "BUN", "eGFR",
    "Uric Acid", "Sodium", "Potassium", "Calcium", "ALT (SGPT)", "AST (SGOT)", "ALP", "Total Bilirubin",
    "Albumin", "Total Protein", "TSH", "Free T4", "Free T3", "Vitamin D", "Vitamin B12", "Ferritin",
    "Iron", "TIBC",
]

STATUS_COLORS = {
    "NORMAL": "background-color:#d4edda;color:#155724",
    "LOW": "background-color:#fff3cd;color:#856404",
    "HIGH": "background-color:#f8d7da;color:#721c24",
    "UNKNOWN": "background-color:#e2e3e5;color:#383d41",
    "UNVERIFIED": "background-color:#e2e3e5;color:#6c757d;font-style:italic",
}

NO_RESULTS_MSG = (
    "No numeric lab results could be found. This tool reads lab test values (blood, urine, lipid and similar "
    "tests). X-ray, ultrasound and ECG reports are not supported yet. For photos, make sure the image is "
    "sharp, upright, and well lit."
)


def color_status(val):
    return STATUS_COLORS.get(val, "")


def get_mime(filename):
    name = filename.lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def parse_num(s):
    """Returns (number or None, ok). Blank is ok and gives None."""
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


def build_table(results):
    rows = []
    for r in results:
        notes = []
        if r.get("flag") == "extreme":
            notes.append("Far outside range - verify and contact a doctor")
        if r.get("verified") is False:
            notes.append("Value or range not matched to the report text - check manually")
        rows.append({
            "Test": r.get("test"),
            "Value": r.get("value"),
            "Unit": r.get("unit"),
            "Low": r.get("ref_low"),
            "High": r.get("ref_high"),
            "Status": str(r.get("status", "unknown")).upper(),
            "Note": "; ".join(notes),
        })
    return pd.DataFrame(rows)


def process_file(uploaded):
    """Returns (results, source, unread). source is 'text' or 'image'."""
    data = uploaded.getvalue()
    mime = get_mime(uploaded.name)
    text = ""
    unread = []
    from_file = mime != "application/pdf"  # images always go straight to the AI

    if not from_file:
        text = extract_text(io.BytesIO(data))
        from_file = looks_scanned(text)  # scanned PDF: no text layer

    if from_file:
        results = extract_results_from_file(data, mime)
    else:
        results = extract_results(text)
        unread = find_unread_lines(results, text)
        results = verify_against_text(results, text)
    return add_status(results), ("image" if from_file else "text"), unread


def finish(results, source, unread, context):
    if not results:
        st.error(NO_RESULTS_MSG)
        return
    with st.spinner("Writing a plain-language explanation..."):
        explanation = explain_results(results, context)
    st.session_state["results"] = results
    st.session_state["explanation"] = explanation
    st.session_state["source"] = source
    st.session_state["unread"] = unread


def run_upload(file, context):
    if file is None:
        st.warning("Please choose a file first.")
        return
    if file.size > MAX_MB * 1024 * 1024:
        st.error(f"This file is too large. Please upload a file under {MAX_MB} MB.")
        return
    try:
        with st.spinner("Reading your report (long reports can take a minute)..."):
            results, source, unread = process_file(file)
        finish(results, source, unread, context)
    except RuntimeError:
        st.error("The AI service is busy right now. Please try again in a minute.")
    except Exception:
        st.error("Something went wrong while reading this report. Please try another file.")


def manual_form():
    if "row_ids" not in st.session_state:
        st.session_state["row_ids"] = [0]
        st.session_state["next_id"] = 1
    ids = st.session_state["row_ids"]
    widths = [3.2, 1.2, 1.2, 1.2, 1.2, 0.6]

    head = st.columns(widths)
    for col, label in zip(head, ["Test name", "Value", "Unit", "Ref. low", "Ref. high", ""]):
        col.caption(label)

    for i in list(ids):
        c = st.columns(widths)
        c[0].selectbox(
            "Test", COMMON_TESTS, index=None, accept_new_options=True,
            placeholder="Search or type a test", key=f"t_{i}", label_visibility="collapsed",
        )
        c[1].text_input("Value", key=f"v_{i}", placeholder="e.g. 11.8", label_visibility="collapsed")
        c[2].text_input("Unit", key=f"u_{i}", placeholder="e.g. g/dL", label_visibility="collapsed")
        c[3].text_input("Ref low", key=f"lo_{i}", placeholder="low", label_visibility="collapsed")
        c[4].text_input("Ref high", key=f"hi_{i}", placeholder="high", label_visibility="collapsed")
        if c[5].button("✕", key=f"del_{i}") and len(ids) > 1:
            ids.remove(i)
            st.rerun()

    if st.button("＋ Add another test", key="add_row"):
        ids.append(st.session_state["next_id"])
        st.session_state["next_id"] += 1
        st.rerun()

    st.caption(
        "Tip: copy the reference range printed next to each value on your report. "
        "Without a range, the result shows as UNKNOWN because the app cannot tell if it is low or high."
    )


def collect_manual():
    results, problems = [], []
    for n, i in enumerate(st.session_state["row_ids"], start=1):
        name = str(st.session_state.get(f"t_{i}") or "").strip()
        raw_value = str(st.session_state.get(f"v_{i}") or "").strip()
        if not name and not raw_value:
            continue  # empty row
        value, ok_v = parse_num(raw_value)
        lo, ok_lo = parse_num(st.session_state.get(f"lo_{i}"))
        hi, ok_hi = parse_num(st.session_state.get(f"hi_{i}"))
        if not name or value is None or not (ok_v and ok_lo and ok_hi):
            problems.append(f"Row {n}: enter a test name and a numeric value, and numbers only for the range.")
            continue
        results.append({
            "test": name,
            "value": value,
            "unit": str(st.session_state.get(f"u_{i}") or "").strip(),
            "ref_low": lo,
            "ref_high": hi,
            "verified": None,
        })
    return results, problems


# ---------------------------------------------------------------- page

st.markdown("""
<style>
.pt {text-align: center; margin: 8px 0 4px 0;}
.pt h1 {font-size: 2.3rem; line-height: 1.2; color: #12313A; margin: 0 0 8px 0;}
.pt p {color: #4A6670; max-width: 640px; margin: 0 auto 14px auto;}
.badges {display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin: 6px 0 18px 0;}
.badges span {background: #F1F8F7; border: 1px solid #D6EAE6; color: #2B5B57; padding: 5px 12px; border-radius: 999px; font-size: .82rem;}
.info {background: #EEF5FF; border: 1px solid #CFE0F7; color: #1F3F66; padding: 14px 16px; border-radius: 12px; font-size: .92rem; margin-bottom: 16px;}
.supported {background: #FFF8E6; border: 1px solid #F5E1A4; color: #6B5300; padding: 10px 14px; border-radius: 10px; font-size: .88rem; margin-bottom: 12px;}
</style>
<div class="pt">
<h1>Interpret your lab results online with AI</h1>
<p>Enter your lab values or upload your report, and get a color-coded table with a plain-language explanation.</p>
</div>
<div class="badges">
<span>📄 PDF and photo support</span>
<span>🔒 Your file is not stored</span>
<span>✅ Values cross-checked with your report</span>
<span>🎨 Color-coded results</span>
</div>
<div class="info"><b>Medical disclaimer.</b> The explanation is generated by AI for educational purposes only. It does not diagnose, treat, or replace advice from a qualified doctor, and it can make mistakes. Always check values against your original report and discuss your results with a healthcare professional.</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown(
        '<div class="supported"><b>Supported:</b> blood, urine, thyroid, lipid, liver, kidney, HbA1c and other '
        'numerical lab results. <b>Not supported yet:</b> ECG, X-ray, ultrasound, CT, MRI and other imaging or '
        'text-only reports.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Patient information** (optional)")
    c1, c2, c3 = st.columns(3)
    age = c1.number_input("Age (years)", min_value=0, max_value=120, value=None, step=1, placeholder="e.g. 45")
    sex = c2.selectbox("Biological sex", ["Prefer not to say", "Female", "Male", "Other"])
    notes = c3.text_input("Clinical notes", placeholder="e.g. diabetic, pregnant", max_chars=200)
    st.caption("Optional. If you fill these in, they are sent to the AI service together with your results.")
    context = build_context(age, sex, notes)

    tab_manual, tab_pdf, tab_img = st.tabs(["✍️ Enter manually", "📄 Upload PDF", "🖼️ Upload image"])

    with tab_manual:
        manual_form()
        if st.button("Interpret my results", type="primary", key="go_manual", width="stretch"):
            manual_results, problems = collect_manual()
            for p in problems:
                st.warning(p)
            if not manual_results:
                st.error("Enter at least one test with a numeric value.")
            else:
                try:
                    finish(add_status(manual_results), "manual", [], context)
                except RuntimeError:
                    st.error("The AI service is busy right now. Please try again in a minute.")
                except Exception:
                    st.error("Something went wrong. Please check your entries and try again.")

    with tab_pdf:
        pdf_file = st.file_uploader("Upload a lab report PDF", type=["pdf"], key="up_pdf")
        if st.button("Interpret my results", type="primary", key="go_pdf", width="stretch"):
            run_upload(pdf_file, context)

    with tab_img:
        img_file = st.file_uploader("Upload a photo or screenshot of your report", type=["png", "jpg", "jpeg"], key="up_img")
        st.caption("Use a sharp, upright, well-lit image. Blurry or tilted photos give worse results.")
        if st.button("Interpret my results", type="primary", key="go_img", width="stretch"):
            run_upload(img_file, context)

if "results" in st.session_state:
    results = st.session_state["results"]
    source = st.session_state.get("source", "text")

    st.subheader("Your results")
    if source == "image":
        st.info(
            "This report was read from an image or scan, so the values were read by AI and could not be "
            "cross-checked automatically. Please compare each value with your original report."
        )
    elif source == "manual":
        st.info(
            "These values were entered manually. The app can only flag low or high when you provide the "
            "reference range from your report."
        )

    table = build_table(results)
    st.dataframe(table.style.map(color_status, subset=["Status"]), width="stretch", hide_index=True)

    if any(r.get("flag") == "extreme" for r in results):
        st.error("One or more values are far outside the reference range. This could be a typing or lab error, or a significant finding. Please contact a doctor promptly.")
    if any(r.get("verified") is False for r in results):
        st.warning("Some rows are marked UNVERIFIED because their numbers could not be matched to the report text. They are not interpreted, so please check them against your original report.")

    unread = st.session_state.get("unread", [])
    if unread:
        with st.expander(f"⚠️ {len(unread)} line(s) in your report may contain results that were not read"):
            st.write("The AI did not pick up these lines. Please check them against your original report:")
            for line in unread:
                st.text(line)

    st.subheader("In plain language")
    st.markdown(st.session_state["explanation"])
    st.caption("This tool can make mistakes. Check every value against your original report.")

    if st.button("Clear results"):
        for key in ("results", "explanation", "source", "unread"):
            st.session_state.pop(key, None)
        st.rerun()

footer()