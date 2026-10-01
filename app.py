import pandas as pd
import streamlit as st

from extractor import extract_text, looks_scanned
from interpreter import extract_results, explain_results, verify_against_text
from rules import add_status

st.set_page_config(page_title="AI Medical Report Interpreter", page_icon="🩺", layout="wide")

st.title("🩺 AI Medical Report Interpreter")
st.warning(
    "For information only. This tool does not diagnose or give medical advice. "
    "Always discuss your results with a doctor."
)

STATUS_COLORS = {
    "NORMAL": "background-color:#d4edda;color:#155724",
    "LOW": "background-color:#fff3cd;color:#856404",
    "HIGH": "background-color:#f8d7da;color:#721c24",
    "UNKNOWN": "background-color:#e2e3e5;color:#383d41",
}


def color_status(val):
    return STATUS_COLORS.get(val, "")


def build_table(results):
    rows = []
    for r in results:
        notes = []
        if r.get("flag") == "extreme":
            notes.append("Far outside range - verify and contact a doctor")
        if not r.get("verified"):
            notes.append("Value not found in report text - check manually")
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


uploaded = st.file_uploader("Upload a lab report (PDF)", type=["pdf"])

if uploaded is None:
    st.info("Upload a text-based PDF lab report to get started.")
    st.stop()

if st.button("Interpret report", type="primary"):
    try:
        with st.spinner("Reading your report..."):
            text = extract_text(uploaded)

        if looks_scanned(text):
            st.error("This looks like a scanned or image-only PDF. Text extraction for scans is not supported yet.")
            st.stop()

        with st.spinner("Extracting results..."):
            results = add_status(verify_against_text(extract_results(text), text))

        if not results:
            st.error("No lab results could be found in this file. Please try a different report.")
            st.stop()

        with st.spinner("Writing a plain-language explanation..."):
            explanation = explain_results(results)

        st.session_state["results"] = results
        st.session_state["explanation"] = explanation

    except RuntimeError:
        st.error("The AI service is busy right now. Please try again in a minute.")
        st.stop()
    except Exception:
        st.error("Something went wrong while reading this report. Please try another file.")
        st.stop()

if "results" in st.session_state:
    results = st.session_state["results"]

    st.subheader("Your results")
    table = build_table(results)
    st.dataframe(table.style.map(color_status, subset=["Status"]), use_container_width=True, hide_index=True)

    if any(r.get("flag") == "extreme" for r in results):
        st.error("One or more values are far outside the reference range. This could be a typing or lab error, or a significant finding. Please contact a doctor promptly.")
    if any(not r.get("verified") for r in results):
        st.warning("Some values could not be matched to the report text. Please check them against your original report.")

    st.subheader("In plain language")
    st.markdown(st.session_state["explanation"])

    st.caption("This tool can make mistakes. Check every value against your original report.")