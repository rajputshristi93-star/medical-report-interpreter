"""Create static translations of the MediLens interface for the languages in i18n.LANGS.

Run from the project folder (it uses your Gemini / Groq setup through interpreter.ask_llm):
    python build_translations.py                   every language that has no file yet
    python build_translations.py --only ta,te,ur   only these language codes
    python build_translations.py --force           redo files that already exist
    python build_translations.py --list            show the language codes

Output: translations/<code>.json. English and Hindi are written by hand inside i18n.py and are skipped.
These are machine translations. Ask a native speaker to review them, above all the medical disclaimer and
the FAQ answers, before real users rely on them.
"""
import argparse
import json
import time

from i18n import BY_CODE, EN, LANGS, TR_DIR, translate_keys

CHUNK = 30


def main(only, force):
    TR_DIR.mkdir(exist_ok=True)
    todo = [l for l in LANGS if l["code"] not in ("en", "hi") and (not only or l["code"] in only)]
    keys = list(EN)
    for lang in todo:
        path = TR_DIR / f"{lang['code']}.json"
        if path.exists() and not force:
            print(f"skip {lang['code']} ({lang['english']}): file exists")
            continue
        result = {}
        for i in range(0, len(keys), CHUNK):
            try:
                result.update(translate_keys(keys[i:i + CHUNK], lang["english"]))
            except Exception as e:
                print(f"  {lang['code']}: a chunk failed ({str(e)[:80]})")
            time.sleep(1)
        if len(result) < 0.9 * len(keys):
            print(f"{lang['code']} ({lang['english']}): only {len(result)}/{len(keys)} keys translated, NOT saved. Run again.")
            continue
        path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{lang['code']} ({lang['english']}): saved {len(result)}/{len(keys)} keys")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma separated codes, for example ta,te,ur")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print(", ".join(f"{l['code']}={l['english']}" for l in LANGS))
    else:
        main({c.strip() for c in a.only.split(",") if c.strip()}, a.force)
