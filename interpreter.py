import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELS = ["gemini-3.8-flash"]  # the only place to change if a model is retired


def ask_llm(prompt, json_mode=False, retries=5):
    config = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    for attempt in range(retries):
        for model in MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt, config=config)
                return response.text
            except errors.ServerError as e:
                print(f"{model} busy ({e.code}), retrying...")
        time.sleep(2 ** attempt)
    raise RuntimeError("LLM is unavailable right now. Please try again later.")


EXTRACT_PROMPT = """You are a data extraction tool. From the lab report text below, extract every test result.

Return ONLY a JSON list. Each item must look like:
{"test": "Hemoglobin", "value": 10.2, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0}

Rules:
- Copy numbers exactly as written in the report. Never correct, guess, or infer values.
- If a reference range is missing, use null for ref_low and ref_high.
- Skip results that are not numeric.

REPORT TEXT:
"""


def _to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def extract_results(report_text):
    raw = ask_llm(EXTRACT_PROMPT + report_text, json_mode=True)
    raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
    results = json.loads(raw)
    for r in results:
        for key in ("value", "ref_low", "ref_high"):
            r[key] = _to_float(r.get(key))
    return results


EXPLAIN_PROMPT = """You are helping a patient understand their lab results in simple language.

Use ONLY the results below. The status column (low/normal/high) was calculated by code, so trust it.

Write three short sections:
1. Summary: 2-3 sentences on the overall picture.
2. What stands out: explain each low or high result, what the test measures, and common general reasons a value can be off. Do not diagnose.
3. Questions to ask your doctor: 3-5 specific questions.

Rules:
- Plain language, no jargon without explanation.
- Do not diagnose, suggest medications, or recommend treatment.
- State clearly that only a doctor can interpret these results properly.
- Do not invent any values.

RESULTS:
"""


def explain_results(results):
    lines = [
        f"{r['test']}: {r['value']} {r.get('unit', '')} "
        f"(range {r['ref_low']} - {r['ref_high']}) -> {r['status']}"
        for r in results
    ]
    return ask_llm(EXPLAIN_PROMPT + "\n".join(lines))