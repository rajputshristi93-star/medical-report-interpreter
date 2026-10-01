# AI Medical Report Interpreter

Upload a lab report (text-based PDF) and get a color-coded results table and a plain-language explanation.

**Not medical advice.** This tool is for information only and does not diagnose. Always discuss results with a doctor.

## How it works
1. `pdfplumber` extracts text from the PDF.
2. An LLM turns the text into structured results (test, value, unit, reference range).
3. Code, not the LLM, decides whether each value is low, normal, or high, and flags extreme values.
4. The LLM explains the results in simple language without diagnosing.
5. Every extracted number is checked against the original report text.

## Run locally
```
pip install -r requirements.txt
```
Create a `.env` file:
```
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
```
Then:
```
streamlit run app.py
```

## Privacy
Uploaded files are processed in memory and not stored by the app. The extracted text is sent to an AI provider (Google Gemini, with Groq as fallback). Use fake or anonymized reports when testing.

## Limitations
- Text-based PDFs only (no scanned images yet)
- Tested on CBC-style reports
- Can make mistakes: always check values against the original report