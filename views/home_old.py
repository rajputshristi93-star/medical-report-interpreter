import streamlit as st

from ui import footer

st.markdown("""
<div class="hero">
<div class="hero-grid">
<div>
<span class="pill">AI-powered · PDF and photo support</span>
<h1>Understand your lab results in plain language</h1>
<p class="lead">Upload a lab report or a clear photo of it. Get a color-coded table and a simple explanation you can take to your doctor.</p>
</div>
<div class="demo">
<b>Example result (sample data)</b>
<table>
<tr><td>Hemoglobin</td><td>11.8 g/dL</td><td><span class="badge b-low">LOW</span></td></tr>
<tr><td>WBC Count</td><td>9.2 ×10³/µL</td><td><span class="badge b-normal">NORMAL</span></td></tr>
<tr><td>Platelets</td><td>420 ×10³/µL</td><td><span class="badge b-high">HIGH</span></td></tr>
</table>
<p class="note">Example only. Not a real patient.</p>
</div>
</div>
</div>
""", unsafe_allow_html=True)

if st.button("Interpret my report →", type="primary"):
    st.switch_page("views/analyze.py")

st.markdown("""
<div class="section-title">How it works</div>
<p class="section-sub">Three steps, no medical background needed.</p>
<div class="grid">
<div class="card"><div class="step-num">1</div><h4>Upload your report</h4><p>PDF, PNG or JPG up to 10 MB. Text PDFs and scans are both supported.</p></div>
<div class="card"><div class="step-num">2</div><h4>AI reads the results</h4><p>Each test, value and reference range is extracted, then checked against the report.</p></div>
<div class="card"><div class="step-num">3</div><h4>Get a clear explanation</h4><p>A color-coded table, a plain-language summary and questions to ask your doctor.</p></div>
</div>
<div class="section-title">What you get</div>
<p class="section-sub">Built to be careful with medical numbers.</p>
<div class="grid">
<div class="card"><h4>📄 PDF and photo upload</h4><p>Read lab reports from text PDFs, scanned PDFs, screenshots and photos.</p></div>
<div class="card"><h4>🎨 Color-coded status</h4><p>Normal, low and high results are easy to spot at a glance.</p></div>
<div class="card"><h4>✅ Cross-checking</h4><p>Extracted numbers are matched to the report text. Anything that does not match is marked, not guessed.</p></div>
<div class="card"><h4>🚨 Extreme value alerts</h4><p>Values far outside the range are highlighted with a prompt to contact a doctor.</p></div>
<div class="card"><h4>🗣️ Plain language</h4><p>Short explanations of what each flagged test measures, without diagnosing.</p></div>
<div class="card"><h4>🩺 Questions for your doctor</h4><p>Specific questions to bring to your appointment.</p></div>
</div>
<div class="section-title">Common questions</div>
""", unsafe_allow_html=True)

with st.expander("Does this diagnose anything?"):
    st.write("No. It explains what the numbers on your report mean in general terms. Only a doctor who knows your history can interpret them for you.")
with st.expander("Is my report stored?"):
    st.write("Your file is processed in memory and is not saved by this app. The file or its extracted text is sent to an AI service to produce the results.")
with st.expander("Which files can I upload?"):
    st.write("PDF, PNG or JPG up to 10 MB. Lab test results (blood, urine, lipid, thyroid and similar) are supported. X-ray, ultrasound and ECG reports are not yet.")
with st.expander("How accurate is it?"):
    st.write("It can make mistakes, especially with blurry photos. Values read from images cannot be cross-checked automatically, so always compare them with your original report.")

footer()