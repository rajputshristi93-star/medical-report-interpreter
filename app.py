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

MAX_MB = 10

st.set_page_config(page_title="AI Medical Report Interpreter", page_icon="🩺", layout="wide")

st.title("🩺 AI Medical Report Interpreter")
st.warning(
    "For information only. This tool does not diagnose or give medical advice. "
    "Always discuss your results with a doctor."
)
st.caption(
    "Privacy: your file is processed in memory and is not saved by this app. "
    "The file or its extracted text is sent to an AI service (Google Gemini, or Groq for text) to generate the results."
)

STATUS_COLORS = {
    "NORMAL": "background-color:#d4edda;color:#155724",
    "LOW": "background-color:#fff3cd;color:#856404",
    "HIGH": "background-color:#f8d7da;color:#721c24",
    "UNKNOWN": "background-color:#e2e3e5;color:#383d41",
    "UNVERIFIED": "background-color:#e2e3e5;color:#6c757d;font-style:italic",
}


def color_status(val):
    return STATUS_COLORS.get(val, "")


def get_mime(filename):
    name = filename.lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".png"):
        return "image/png"
    return "image/jpeg"


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


uploaded = st.file_uploader("Upload a lab report (PDF or image)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded is None:
    for key in ("results", "explanation", "from_file", "unread"):
        st.session_state.pop(key, None)
    st.info("Upload a lab report as a PDF, or a clear photo or screenshot, to get started.")
    st.stop()

if uploaded.size > MAX_MB * 1024 * 1024:
    st.error(f"This file is too large. Please upload a file under {MAX_MB} MB.")
    st.stop()

if st.button("Interpret report", type="primary"):
    try:
        data = uploaded.getvalue()
        mime = get_mime(uploaded.name)
        text = ""
        unread = []
        from_file = mime != "application/pdf"  # images always go straight to the AI

        if not from_file:
            with st.spinner("Reading your report..."):
                text = extract_text(io.BytesIO(data))
            from_file = looks_scanned(text)  # scanned PDF: no text layer

        with st.spinner("Extracting results (long reports can take a minute)..."):
            if from_file:
                results = extract_results_from_file(data, mime)
            else:
                results = extract_results(text)
                unread = find_unread_lines(results, text)
                results = verify_against_text(results, text)
            results = add_status(results)

        if not results:
            st.error(
                "No numeric lab results could be found. This tool reads lab test values "
                "(blood, urine, lipid and similar tests). X-ray, ultrasound and ECG reports are not supported yet. "
                "For photos, make sure the image is sharp, upright, and well lit."
            )
            st.stop()

        with st.spinner("Writing a plain-language explanation..."):
            explanation = explain_results(results)

        st.session_state["results"] = results
        st.session_state["explanation"] = explanation
        st.session_state["from_file"] = from_file
        st.session_state["unread"] = unread

    except RuntimeError:
        st.error("The AI service is busy right now. Please try again in a minute.")
        st.stop()
    except Exception:
        st.error("Something went wrong while reading this report. Please try another file.")
        st.stop()

if "results" in st.session_state:
    results = st.session_state["results"]

    st.subheader("Your results")
    if st.session_state.get("from_file"):
        st.info(
            "This report was read from an image or scan, so the values were read by AI and could not be "
            "cross-checked automatically. Please compare each value with your original report."
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