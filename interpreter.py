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

MAX_CHUNKS = 12  # safety cap on requests per pass
IMAGING_UNITS = {"mm", "cm", "cc"}

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
- Copy the test name exactly as printed in the report.
- Copy numbers exactly as printed. Never correct, guess, or infer values.
- If a value is unclear or unreadable, skip it.
- If a reference range is missing, use null for ref_low and ref_high.
- A range like "<200" means ref_low null and ref_high 200. A range like ">40" means ref_low 40 and ref_high null. Copy every digit of the limit.
- Skip results that are not numeric (for example Negative, Pale Yellow, NIL).
- Ignore patient details, dates, lab address, methods, and explanatory notes.
- Ignore imaging and radiology findings (ultrasound, X-ray, ECG), such as organ sizes in mm or cm.
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
        unit = str(r.get("unit") or "")
        lo, hi = _to_float(r.get("ref_low")), _to_float(r.get("ref_high"))
        if unit.lower() in IMAGING_UNITS and lo is None and hi is None:
            continue  # organ sizes from ultrasound and similar, not lab tests
        out.append({"test": name, "value": value, "unit": unit, "ref_low": lo, "ref_high": hi})
    return out


def _dedupe(results):
    seen, out = set(), []
    for r in results:
        key = (r["test"].lower(), r["value"], r["unit"].lower())
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _chunk_lines(lines, max_chars=2000, overlap=3):
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


# ---------- number helpers (verification and finding missed rows) ----------

NUM_RE = re.compile(r"(?<![\d.])\d+(?:\.\d+)?")

# A line that looks like: <name> <value> <unit> <range>, for example "Mean Corpuscular Volume (MCV) 93.3 fL 83 - 101"
ROW_RE = re.compile(
    r"[A-Za-z\)\]]\s+\d+(?:\.\d+)?\s+\S+\s+"
    r"(?:\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?|[<>]=?\s*\d+(?:\.\d+)?)"
)


def _numbers_in(line):
    return {round(float(m), 6) for m in NUM_RE.findall(line.replace(",", ""))}


def _name_tokens(name):
    return re.findall(r"[a-z]{3,}", str(name).lower())


def _strip_start(s):
    return re.sub(r"^[^a-z0-9]+", "", s.lower())


def _first_word(name):
    m = re.match(r"[a-z0-9]+", _strip_start(str(name)))
    return m.group(0) if m else ""


def _is_covered(line_low, line_nums, results):
    for r in results:
        v = r.get("value")
        if v is None or round(v, 6) not in line_nums:
            continue
        tokens = _name_tokens(r.get("test", ""))
        if not tokens or any(t in line_low for t in tokens):
            return True
    return False


def _missed_lines(results, lines):
    """Lines that look like result rows but no extracted result accounts for them."""
    out = []
    for line in lines:
        nums = _numbers_in(line)
        looks_like_row = len(nums) >= 2 or (nums and ("<" in line or ">" in line))
        if looks_like_row and re.search(r"[A-Za-z]{3,}", line) and not _is_covered(line.lower(), nums, results):
            out.append(line)
    return out


def _run_chunks(lines):
    out = []
    for chunk in _chunk_lines(lines)[:MAX_CHUNKS]:
        raw = ask_llm(EXTRACT_PROMPT + "\nREPORT TEXT:\n" + chunk, json_mode=True)
        out.extend(_clean(_parse_json_list(raw)))
    return out


def extract_results(report_text):
    """For PDFs that contain real text. Long reports are split into chunks, then checked for missed rows."""
    lines = clean_lines(report_text)
    results = _dedupe(_run_chunks(lines))

    missed = _missed_lines(results, lines)[:150]
    if missed:
        print(f"Second pass over {len(missed)} lines the first pass did not cover...")
        results = _dedupe(results + _run_chunks(missed))
    return results


def find_unread_lines(results, text):
    """Lines that clearly look like result rows (name, value, unit, range) but were not extracted."""
    lines = clean_lines(text)
    return [ln for ln in _missed_lines(results, lines) if ROW_RE.search(ln)][:30]


def extract_results_from_file(data, mime_type):
    """For images (PNG/JPG) and scanned PDFs. Gemini reads the file directly."""
    part = types.Part.from_bytes(data=data, mime_type=mime_type)
    raw = ask_llm([part, EXTRACT_PROMPT], json_mode=True, vision=True)
    results = _dedupe(_clean(_parse_json_list(raw)))
    for r in results:
        r["verified"] = None  # no text layer to cross-check against
    return results


def verify_against_text(results, text):
    """True only if one line of the report STARTS with the test name and contains the value and its range limits."""
    rows = [(_strip_start(line), _numbers_in(line)) for line in text.splitlines()]
    for r in results:
        v = r.get("value")
        word = _first_word(r.get("test", ""))
        if v is None or not word:
            r["verified"] = False
            continue
        needed = {round(n, 6) for n in (v, r.get("ref_low"), r.get("ref_high")) if n is not None}
        r["verified"] = any(low.startswith(word) and needed <= nums for low, nums in rows)
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
- Do not state any reference range, threshold, or "normal" value that is not listed below.
- Do not call a result high, low, or abnormal unless its status below says so.
- For unusual or abbreviated tests (for example P-LCC or Mentzer Index), do NOT explain what they measure and do NOT guess. Just state the value and status and suggest asking the doctor what it means.
- If a result is marked EXTREME, say it is far outside the range, that it could be a typing or lab error or a significant finding, and advise contacting a doctor promptly rather than waiting.
- Group related results together (for example kidney tests, liver tests, blood count) instead of repeating yourself.

RESULTS:
"""


def explain_results(results, context=""):
    lines = []
    for r in results:
        if r.get("status") in ("low", "high"):
            line = (f"{r['test']}: {r['value']} {r.get('unit', '')} "
                    f"(range {r['ref_low']} - {r['ref_high']}) -> {r['status']}")
            if r.get("flag") == "extreme":
                line += " [EXTREME]"
            lines.append(line)
    normal = sum(1 for r in results if r.get("status") == "normal")
    lines.append(f"{normal} other results are within their reference ranges.")

    unknown = [r for r in results if r.get("status") == "unknown"]
    if unknown:
        lines.append(
            "Results with no reference range in the report (do not call these high or low; "
            "mention them neutrally and suggest asking the doctor about them):"
        )
        for r in unknown[:15]:
            lines.append(f"- {r['test']}: {r['value']} {r.get('unit', '')}")

    unverified = [r for r in results if r.get("status") == "unverified"]
    if unverified:
        lines.append(
            "Results that could not be matched to the report text (do NOT interpret these; "
            "tell the patient to check them against the original report):"
        )
        for r in unverified[:15]:
            lines.append(f"- {r['test']}: {r['value']} {r.get('unit', '')}")
    if context:
        lines.insert(0, "Optional background from the user (do not diagnose from it; use it only to make the explanation more relevant):\n" + context + "\n")
    return ask_llm(EXPLAIN_PROMPT + "\n".join(lines))