import os
import re
import json
import time
import hashlib
import pathlib
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from extractor import clean_lines

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if (Groq and os.getenv("GROQ_API_KEY")) else None

GEMINI_MODELS = ["gemini-3.8-flash"]
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]  # text only, used as fallback

# Dev-only cache so repeated test runs don't spend quota. Fake reports only.
USE_CACHE = os.getenv("LLM_CACHE", "0") == "1"
CACHE_DIR = pathlib.Path(".llm_cache")

MAX_CHUNKS = 12  # safety cap on requests per report

_gemini_paused_until = 0.0


def _call_gemini(prompt, json_mode):
    """prompt can be a string, or a list like [file_part, "instructions"]."""
    global _gemini_paused_until
    if time.time() < _gemini_paused_until:
        return None
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
        except Exception as e:
            print(f"Gemini {model} network error: {str(e)[:100]}")
    return None


def _call_groq(prompt, json_mode):
    if groq_client is None or not isinstance(prompt, str):
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


def ask_llm(prompt, json_mode=False, retries=4, vision=False):
    """vision=True means the prompt contains an image or PDF, so only Gemini can be used."""
    cache_file = None
    if USE_CACHE and isinstance(prompt, str):
        CACHE_DIR.mkdir(exist_ok=True)
        key = hashlib.sha256((prompt + str(json_mode)).encode()).hexdigest()
        cache_file = CACHE_DIR / f"{key}.txt"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

    providers = (_call_gemini,) if vision else (_call_gemini, _call_groq)

    for attempt in range(retries):
        for provider in providers:
            text = provider(prompt, json_mode)
            if text:
                if cache_file:
                    cache_file.write_text(text, encoding="utf-8")
                return text
        wait = 10 * (attempt + 1)
        print(f"AI busy. Waiting {wait}s (attempt {attempt + 1}/{retries})...")
        time.sleep(wait)

    raise RuntimeError("The AI service is busy right now. Please try again in a few minutes.")


EXTRACT_PROMPT = """You are a data extraction tool. From the lab report provided, extract every numeric test result.

Return ONLY a JSON list. Each item must look like:
{"test": "Hemoglobin", "value": 10.2, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0}

Rules:
- Copy numbers exactly as printed. Never correct, guess, or infer values.
- If a value is unclear or unreadable, skip it.
- If a reference range is missing, use null for ref_low and ref_high.
- A range like "<200" means ref_low null and ref_high 200. A range like ">40" means ref_low 40 and ref_high null.
- Skip results that are not numeric (for example Negative, Pale Yellow, NIL).
- Ignore patient details, dates, lab address, methods, and explanatory notes.
- Include every test from every table and every page.
"""


def _to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _parse_json_list(raw):
    """Parses the AI answer. If the JSON is cut off, still recovers every complete item."""
    raw = (raw or "").strip()
    cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        if isinstance(data, dict):
            lists = [v for v in data.values() if isinstance(v, list)]
            return [r for r in (lists[0] if lists else [data]) if isinstance(r, dict)]
    except json.JSONDecodeError:
        pass
    items = []
    for m in re.finditer(r"\{[^{}]*\}", raw):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                items.append(obj)
        except json.JSONDecodeError:
            continue
    return items


def _clean(items):
    out = []
    for r in items:
        name = str(r.get("test") or "").strip()
        value = _to_float(r.get("value"))
        if not name or value is None:
            continue
        out.append({
            "test": name,
            "value": value,
            "unit": str(r.get("unit") or ""),
            "ref_low": _to_float(r.get("ref_low")),
            "ref_high": _to_float(r.get("ref_high")),
        })
    return out


def _dedupe(results):
    seen, out = set(), []
    for r in results:
        key = (r["test"].lower(), r["value"], r["unit"].lower())
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _chunk_lines(lines, max_chars=2500, overlap=3):
    chunks, cur, size = [], [], 0
    for line in lines:
        if size + len(line) > max_chars and cur:
            chunks.append("\n".join(cur))
            cur = cur[-overlap:]  # small overlap so a test name is not split from its value
            size = sum(len(x) + 1 for x in cur)
        cur.append(line)
        size += len(line) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def extract_results(report_text):
    """For PDFs that contain real text. Splits long reports into chunks."""
    chunks = _chunk_lines(clean_lines(report_text))[:MAX_CHUNKS]
    results = []
    for chunk in chunks:
        raw = ask_llm(EXTRACT_PROMPT + "\nREPORT TEXT:\n" + chunk, json_mode=True)
        results.extend(_clean(_parse_json_list(raw)))
    return _dedupe(results)


def extract_results_from_file(data, mime_type):
    """For images (PNG/JPG) and scanned PDFs. Gemini reads the file directly."""
    part = types.Part.from_bytes(data=data, mime_type=mime_type)
    raw = ask_llm([part, EXTRACT_PROMPT], json_mode=True, vision=True)
    results = _dedupe(_clean(_parse_json_list(raw)))
    for r in results:
        r["verified"] = None  # no text layer to cross-check against
    return results


def verify_against_text(results, text):
    """Marks a row True only if its number appears on a line that mentions the test name."""
    lines = [line.replace(",", "") for line in text.splitlines()]
    for r in results:
        v = r.get("value")
        if v is None:
            r["verified"] = False
            continue
        forms = {str(v), f"{v:.10g}", f"{v:.2f}"}
        tokens = re.findall(r"[a-z]{3,}", str(r.get("test", "")).lower())
        ok = False
        for line in lines:
            low = line.lower()
            if tokens and not any(t in low for t in tokens):
                continue
            if any(re.search(rf"(?<![\d.]){re.escape(f)}(?!\d|\.\d)", line) for f in forms):
                ok = True
                break
        r["verified"] = ok
    return results


EXPLAIN_PROMPT = """You are helping a patient understand their lab results in simple language.

Use ONLY the results below. The status (low/high) was calculated by code, so trust it.

Write three short sections:
1. Summary: 2-3 sentences on the overall picture.
2. What stands out: for each low or high result, say what the test measures and common general reasons a value can be off. Do not diagnose.
3. Questions to ask your doctor: 3-5 specific questions.

Rules:
- Plain language, no jargon without explanation.
- Do not diagnose, suggest medications, or recommend treatment.
- State clearly that only a doctor can interpret these results properly.
- Do not invent any values.
- If a result is marked EXTREME, say it is far outside the range, that it could be a typing or lab error or a significant finding, and advise contacting a doctor promptly rather than waiting.
- Group related results together (for example kidney tests, liver tests, blood count) instead of repeating yourself.

RESULTS:
"""


def explain_results(results):
    lines = []
    for r in results:
        if r.get("status") in ("low", "high"):
            line = (f"{r['test']}: {r['value']} {r.get('unit', '')} "
                    f"(range {r['ref_low']} - {r['ref_high']}) -> {r['status']}")
            if r.get("flag") == "extreme":
                line += " [EXTREME]"
            lines.append(line)
    normal = sum(1 for r in results if r.get("status") == "normal")
    unknown = sum(1 for r in results if r.get("status") == "unknown")
    lines.append(f"{normal} other results are within their reference ranges.")
    if unknown:
        lines.append(f"{unknown} results had no reference range to compare against.")
    return ask_llm(EXPLAIN_PROMPT + "\n".join(lines))