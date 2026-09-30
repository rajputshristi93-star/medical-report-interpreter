import os
import json
import time
import hashlib
import pathlib
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if (Groq and os.getenv("GROQ_API_KEY")) else None

# Add more names to either list as fallbacks (quotas are per model).
GEMINI_MODELS = ["gemini-3.8-flash"]
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]  # check console.groq.com/docs/models for current names

# Dev-only cache so repeated test runs don't spend quota.
# It saves report text on disk, so use it with fake reports only.
USE_CACHE = os.getenv("LLM_CACHE", "0") == "1"
CACHE_DIR = pathlib.Path(".llm_cache")


_gemini_paused_until = 0.0


def _call_gemini(prompt, json_mode):
    global _gemini_paused_until
    if time.time() < _gemini_paused_until:
        return None  # skip Gemini while it is rate limited
    config = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    for model in GEMINI_MODELS:
        try:
            response = gemini_client.models.generate_content(model=model, contents=prompt, config=config)
            return response.text
        except errors.ServerError as e:
            print(f"Gemini {model} busy ({e.code})")
        except errors.ClientError as e:
            if e.code == 429:
                print(f"Gemini {model} rate limit reached, pausing Gemini for 60s")
                _gemini_paused_until = time.time() + 60
            else:
                print(f"Gemini {model} error {e.code}")
        except Exception as e:  # network problems such as DNS failures
            print(f"Gemini {model} network error: {str(e)[:100]}")
    return None


def _call_groq(prompt, json_mode):
    if groq_client is None:
        return None
    for model in GROQ_MODELS:
        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq {model} failed: {str(e)[:150]}")
    return None


def ask_llm(prompt, json_mode=False, retries=4):
    cache_file = None
    if USE_CACHE:
        CACHE_DIR.mkdir(exist_ok=True)
        key = hashlib.sha256((prompt + str(json_mode)).encode()).hexdigest()
        cache_file = CACHE_DIR / f"{key}.txt"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

    for attempt in range(retries):
        for provider in (_call_gemini, _call_groq):
            text = provider(prompt, json_mode)
            if text:
                if cache_file:
                    cache_file.write_text(text, encoding="utf-8")
                return text
        wait = 10 * (attempt + 1)
        print(f"All providers busy. Waiting {wait}s (attempt {attempt + 1}/{retries})...")
        time.sleep(wait)

    raise RuntimeError("The AI service is busy right now. Please try again in a few minutes.")


EXTRACT_PROMPT = """You are a data extraction tool. From the lab report text below, extract every test result.

Return ONLY a JSON list. Each item must look like:
{"test": "Hemoglobin", "value": 10.2, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0}

Rules:
- Copy numbers exactly as written in the report. Never correct, guess, or infer values.
- If a reference range is missing, use null for ref_low and ref_high.
- A range like "<200" means ref_low null and ref_high 200. A range like ">40" means ref_low 40 and ref_high null.
- Skip results that are not numeric.
- Ignore patient details, dates, and lab address.

REPORT TEXT:
"""


def _to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _parse_json_list(raw):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), [])
    return [r for r in data if isinstance(r, dict)]


def extract_results(report_text):
    raw = ask_llm(EXTRACT_PROMPT + report_text, json_mode=True)
    results = _parse_json_list(raw)
    for r in results:
        for key in ("value", "ref_low", "ref_high"):
            r[key] = _to_float(r.get(key))
    return results


def verify_against_text(results, text):
    """Marks each row True only if its number really appears in the report text."""
    clean = text.replace(",", "")
    for r in results:
        v = r.get("value")
        if v is None:
            r["verified"] = False
        else:
            r["verified"] = f"{v:.10g}" in clean or str(v) in clean
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
- If a result is marked EXTREME, say it is far outside the range, that it could be a typing or lab error or a significant finding, and advise contacting a doctor promptly rather than waiting.

RESULTS:
"""


def explain_results(results):
    lines = []
    for r in results:
        line = (f"{r['test']}: {r['value']} {r.get('unit', '')} "
                f"(range {r['ref_low']} - {r['ref_high']}) -> {r['status']}")
        if r.get("flag") == "extreme":
            line += " [EXTREME]"
        lines.append(line)
    return ask_llm(EXPLAIN_PROMPT + "\n".join(lines))