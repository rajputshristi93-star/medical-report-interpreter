"""Experimental multi-condition pattern screening for MediLens AI.

Uses the models trained by train_nhanes_model.py (models/nhanes_models.joblib + .json).
It never shows a percentage and never says 'you have'. It only says whether the values
resemble the pattern linked to a condition in the (US, self-reported) training data.
"""
import json
import os
import re

MODEL_DIR = "models"
_CACHE = {}

MG, GDL = ("mg/dl", "mg%"), ("g/dl", "gm/dl", "gm%", "g%")
UL = ("u/l", "iu/l", "u/litre", "iu/litre")
MMOL = ("mmol/l", "meq/l")
K3 = ("x103/µl", "103/µl", "x109/l", "109/l", "k/µl", "thou/µl", "x10e3/µl", "10e3/µl", "x103/mm3", "103/mm3")
PER_UL = {"/µl": 1e-3, "cells/µl": 1e-3, "/mm3": 1e-3, "cells/mm3": 1e-3, "/cumm": 1e-3, "cumm": 1e-3}
LAKH = {"lakh/cumm": 100, "lakhs/cumm": 100, "lakh/µl": 100, "lakhs/µl": 100, "lakh/mm3": 100, "lakhs/mm3": 100}
RBC_BASE = ("million/µl", "mill/µl", "mil/µl", "millions/µl", "106/µl", "x106/µl", "1012/l", "x1012/l", "m/µl")
DEFAULT_EXCLUDE = r"ratio|urin|/|average|avg|index|clearance|absolute"


def S(label, unit, match, base, bounds, conv=None, exclude=DEFAULT_EXCLUDE, scale=1.0):
    return dict(label=label, unit=unit, match=match, base=base, bounds=bounds, conv=conv or {},
                exclude=exclude, scale=scale)


SPECS = {
    "hemoglobin": [S("Hemoglobin", "g/dL", r"^h[ae]moglobin(\s*\(hb\))?$|^hb$", GDL, (3, 25), {"g/l": .1})],
    "hematocrit": [S("Hematocrit", "%", r"^h[ae]matocrit|^pcv|packed cell volume", ("%",), (10, 70))],
    "rbc": [S("RBC count", "million/µL", r"^(total\s+)?rbc(\s*count)?$|^red blood cells?(\s*count)?$", RBC_BASE,
              (1.5, 9), {"/µl": 1e-6, "/mm3": 1e-6, "/cumm": 1e-6})],
    "wbc": [S("WBC count", "10^3/µL", r"wbc|^total\s+leu[ck]ocyte|^leu[ck]ocyte\s+count|^tlc$", K3,
              (0.5, 100), PER_UL)],
    "platelets": [S("Platelet count", "10^3/µL", r"^platelets?(\s*count)?$|^plt(\s*count)?$", K3,
                    (10, 1500), {**PER_UL, **LAKH})],
    "mcv": [S("MCV", "fL", r"^mcv$|^mean corpuscular volume(\s*\(mcv\))?$", ("fl", "µm3", "um3"), (50, 150))],
    "mch": [S("MCH", "pg", r"^mch$|^mean corp(uscular)?\.?\s*h[ae]moglobin(\s*\(mch\))?$", ("pg",), (10, 50))],
    "mchc": [S("MCHC", "g/dL", r"^mchc$|^mch\s*concentration|mean corp(uscular)?\.?\s*h[ae]moglobin\s*conc",
               GDL + ("%",), (20, 45), {"g/l": .1})],
    "rdw": [S("RDW (CV)", "%", r"rdw[-\s]*cv|^rdw$|^red cell dist(ribution)?\.?\s*width(\s*\(rdw-?cv\))?$",
              ("%",), (8, 30), exclude=DEFAULT_EXCLUDE + r"|sd")],
    "hba1c": [S("HbA1c", "%", r"hba1c|a1c|glycosylated|glycated|glycohemoglobin", ("%",), (3, 20))],
    "glucose": [S("Glucose", "mg/dL", r"glucose|blood sugar|^fbs$|^fasting (blood )?sugar|^rbs$", MG, (30, 800),
                  {"mmol/l": 18.016}, exclude=DEFAULT_EXCLUDE + r"|post|pp|2h|2-h|tolerance|ogtt")],
    "creatinine": [S("Creatinine", "mg/dL", r"^(serum\s+)?creatinine(,\s*serum)?$", MG, (0.2, 15),
                     {"µmol/l": 1 / 88.4, "umol/l": 1 / 88.4})],
    "bun": [S("Blood urea nitrogen", "mg/dL", r"^bun$|blood urea nitrogen|^urea nitrogen", MG, (2, 150),
              {"mmol/l": 2.801}),
            S("Blood urea (as BUN)", "mg/dL", r"^(blood |serum )?urea$", MG, (2, 150), {"mmol/l": 6.006},
              scale=0.4667)],
    "uric_acid": [S("Uric acid", "mg/dL", r"uric acid", MG, (1, 20),
                    {"µmol/l": 1 / 59.48, "umol/l": 1 / 59.48, "mmol/l": 16.81})],
    "sodium": [S("Sodium", "mmol/L", r"^(serum\s+)?sodium(\s*\(na\))?$|^na$", MMOL, (100, 180))],
    "potassium": [S("Potassium", "mmol/L", r"^(serum\s+)?potassium(\s*\(k\))?$|^k$", MMOL, (2, 9))],
    "chloride": [S("Chloride", "mmol/L", r"^(serum\s+)?chloride(\s*\(cl\))?$", MMOL, (70, 130))],
    "calcium": [S("Calcium", "mg/dL", r"^(serum\s+|total\s+)?calcium(,\s*total)?$", MG, (5, 15), {"mmol/l": 4.008})],
    "phosphorus": [S("Phosphorus", "mg/dL", r"phosph(o|a)rus|inorganic phosphate", MG, (1, 10), {"mmol/l": 3.097},
                     exclude=DEFAULT_EXCLUDE + r"|alkaline")],
    "albumin": [S("Albumin", "g/dL", r"^(serum\s+|s\.?\s*)?albumin$", GDL, (1, 7), {"g/l": .1})],
    "total_protein": [S("Total protein", "g/dL", r"total\s*proteins?", GDL, (3, 12), {"g/l": .1})],
    "globulin": [S("Globulin", "g/dL", r"^(serum\s+)?globulin$", GDL, (1, 6), {"g/l": .1})],
    "total_bilirubin": [S("Total bilirubin", "mg/dL", r"total\s*bilirubin|bilirubin\s*[,\-]?\s*total|^t\.?\s*bilirubin",
                          MG, (0.05, 60), {"µmol/l": 1 / 17.1, "umol/l": 1 / 17.1})],
    "alt": [S("ALT (SGPT)", "U/L", r"\balt\b|sgpt|alanine|alamine", UL, (1, 5000))],
    "ast": [S("AST (SGOT)", "U/L", r"\bast\b|sgot|aspartate", UL, (1, 5000))],
    "alk_phos": [S("Alkaline phosphatase", "U/L", r"alkaline\s*phosph|alk\.?\s*phos|\balp\b", UL, (10, 3000))],
    "ggt": [S("GGT", "U/L", r"\bggt\b|gamma\s*glutamyl|\bgamma\s*gt\b", UL, (1, 3000))],
    "total_cholesterol": [S("Total cholesterol", "mg/dL", r"^(total\s+|serum\s+)?cholesterol(,?\s*total)?$", MG,
                            (50, 600), {"mmol/l": 38.67}, exclude=DEFAULT_EXCLUDE + r"|ldl|hdl|vldl|non")],
    "triglycerides": [S("Triglycerides", "mg/dL", r"triglycerid", MG, (20, 3000), {"mmol/l": 88.57})],
    "hdl": [S("HDL cholesterol", "mg/dL", r"\bhdl\b", MG, (10, 150), {"mmol/l": 38.67},
              exclude=DEFAULT_EXCLUDE + r"|non")],
    "ldl": [S("LDL cholesterol", "mg/dL", r"\bldl\b", MG, (10, 500), {"mmol/l": 38.67},
              exclude=DEFAULT_EXCLUDE + r"|non")],
}


def _paths():
    return os.path.join(MODEL_DIR, "nhanes_models.joblib"), os.path.join(MODEL_DIR, "nhanes_model.json")


def is_available():
    return all(os.path.exists(p) for p in _paths())


def load_card():
    with open(_paths()[1], encoding="utf-8") as f:
        return json.load(f)


def _bundle():
    if "bundle" not in _CACHE:
        import joblib
        _CACHE["bundle"] = joblib.load(_paths()[0])
    return _CACHE["bundle"]


def _unit_key(u):
    u = str(u or "").strip().lower().replace(" ", "").replace("μ", "µ").replace("³", "3")
    u = u.replace("^", "").replace("×", "x")
    return re.sub(r"/ul$", "/µl", u).replace("mill/ul", "mill/µl")


def _to_standard(value, unit, spec):
    """Returns (value in the model's unit, reason). Unknown units are never guessed."""
    u, (lo, hi) = _unit_key(unit), spec["bounds"]
    if u in spec["base"]:
        v = value
    elif u in spec["conv"]:
        v = value * spec["conv"][u]
    elif u == "":
        v = value
        if not lo <= v <= hi and "/µl" in spec["conv"]:
            v = value * spec["conv"]["/µl"]  # a count written per µL without a unit
        if not lo <= v <= hi:
            return None, "no unit given and the value looks implausible"
    else:
        return None, f"unit '{unit}' not recognised"
    v *= spec["scale"]
    if not lo <= v <= hi:
        return None, "value outside the plausible range, please check it"
    return v, ""


def _find(results, variants):
    for spec in variants:
        for r in results:
            name = re.sub(r"\s+", " ", str(r.get("test", "")).strip().lower())
            if r.get("value") is None or r.get("verified") is False or r.get("status") == "unverified":
                continue
            if re.search(spec["match"], name) and not re.search(spec["exclude"], name):
                return r, spec
    return None


def assess(results, age, sex):
    """state: unavailable | need_info | age | ok. Per condition: similar | not_similar | in_range | not_enough."""
    out = {"state": "", "per": {}, "used": 0, "notes": []}
    if not is_available():
        out["state"] = "unavailable"
        return out
    if age is None or sex not in ("Female", "Male"):
        out["state"] = "need_info"
        return out
    if not 18 <= age <= 90:
        out["state"] = "age"
        return out

    import numpy as np
    import pandas as pd
    card, bundle = load_card(), _bundle()
    feats = bundle["features"]
    vec = {f: np.nan for f in feats}
    present, abnormal, labels = set(), set(), {}
    for feat, variants in SPECS.items():
        labels[feat] = variants[0]["label"]
        if feat not in vec:
            continue
        found = _find(results, variants)
        if not found:
            continue
        row, spec = found
        v, why = _to_standard(float(row["value"]), row.get("unit"), spec)
        if v is None:
            out["notes"].append(f"{spec['label']}: {why}")
            continue
        vec[feat] = v
        present.add(feat)
        if row.get("status") in ("low", "high"):
            abnormal.add(feat)
    vec["age"], vec["sex_male"] = float(age), 1.0 if sex == "Male" else 0.0
    X = pd.DataFrame([vec])[feats]
    out["used"] = len(present)

    for key in bundle["enabled"]:
        keyf = card["key_features"][key]
        have = [f for f in keyf if f in present]
        info = {"title": card["titles"][key], "needs": [labels.get(f, f) for f in keyf]}
        if len(have) < min(2, len(keyf)):
            info["result"] = "not_enough"
        elif not set(have) & abnormal:
            info["result"] = "in_range"  # no key value is outside the report's own range
        else:
            score = float(bundle["models"][key].predict_proba(X)[0, 1])
            info["result"] = "similar" if score >= bundle["thresholds"][key] else "not_similar"
        out["per"][key] = info
    out["state"] = "ok"
    return out


_STATIC = [
    "Pattern screening (experimental)",
    "Experimental and for learning only. Small models trained on public US survey data compare your values with patterns linked to some conditions. They can be wrong, they are not a diagnosis, and they show no percentages. Only a doctor can tell what your results mean.",
    "Run the screening", "Age (years)", "Biological sex", "Select", "Female", "Male",
    "Needed by the models. Used only for this check and not saved.", "Run screening",
    "Please enter your age and biological sex first.", "These models were built for adults (18 to 90 years).",
    "Your values resemble the pattern linked to:", "This is not a diagnosis. Please discuss these results with a doctor.",
    "No strong pattern found for:", "This does not mean everything is fine. Your doctor decides what your results mean.",
    "Not run, because the key values are within range:", "About these models",
    "Not enough values to check", "Needs two of:", "values from your report were used. More values give a more reliable check.",
    "test ROC-AUC", "In testing, about", "of the people it flagged really had it", "of all people had it",
    "Evaluated, but not shown to users", "excluded by design", "accuracy below the quality bar",
    "lab values add little beyond age and sex", "Not shown:", "age and sex alone", "Only conditions that passed a quality check are shown. Limits:",
]


def render_ml_section(embedded=False):
    """Opt-in experimental section. Nothing is stored."""
    import streamlit as st
    from i18n import localize

    results = st.session_state.get("results")
    if not results:
        return
    if not is_available():
        if embedded:
            st.info(localize(["The screening models are not installed on this server."])["The screening models are not installed on this server."])
        return
    card = load_card()
    M = localize(list(_STATIC) + list(card.get("titles", {}).values()))
    L = lambda s: M.get(s, s)
    title = lambda k: M.get(card["titles"][k], card["titles"][k])

    if not embedded:
        st.divider()
        st.subheader("🧠 " + L(_STATIC[0]))
    st.warning(L(_STATIC[1]))
    with st.expander(L(_STATIC[2]), expanded=False):
        c1, c2 = st.columns(2)
        age = c1.number_input(L(_STATIC[3]), min_value=0, max_value=120, value=None, step=1, key="ml_age")
        sex = c2.selectbox(L(_STATIC[4]), ["Select", "Female", "Male"], key="ml_sex", format_func=L)
        st.caption(L(_STATIC[8]))

        if st.button(L(_STATIC[9]), key="ml_go"):
            res = assess(results, age, sex)
            if res["state"] == "need_info":
                st.info(L(_STATIC[10]))
            elif res["state"] == "age":
                st.info(L(_STATIC[11]))
            elif res["state"] == "ok":
                per = res["per"]
                groups = {k: [v for v in per.values() if v["result"] == k]
                          for k in ("similar", "not_similar", "in_range", "not_enough")}
                name = lambda v: M.get(v["title"], v["title"])
                if groups["similar"]:
                    st.warning(f"{L(_STATIC[12])} {', '.join(name(v) for v in groups['similar'])}. {L(_STATIC[13])}")
                if groups["not_similar"]:
                    st.success(f"{L(_STATIC[14])} {', '.join(name(v) for v in groups['not_similar'])}. {L(_STATIC[15])}")
                if groups["in_range"]:
                    st.info(f"{L(_STATIC[16])} {', '.join(name(v) for v in groups['in_range'])}.")
                for v in groups["not_enough"]:
                    st.caption(f"{L(_STATIC[18])} {name(v)}. {L(_STATIC[19])} {', '.join(v['needs'])}.")
                st.caption(f"{res['used']} {L(_STATIC[20])}")
                N = localize(res["notes"])
                for n in res["notes"]:
                    st.caption(N.get(n, n))

    with st.expander(L(_STATIC[17])):
        D = localize([card.get("dataset", "")] + list(card.get("limitations", [])))
        st.write(D.get(card.get("dataset", ""), card.get("dataset", "")))
        for k in card.get("enabled", []):
            m = card["results"][k]
            st.markdown(f"- **{title(k)}**: {L(_STATIC[21])} {m['roc_auc']:.2f}. {L(_STATIC[22])} "
                        f"{m['precision_at_threshold']:.0%} {L(_STATIC[23])} ({m['prevalence']:.0%} {L(_STATIC[24])}).")
        others = [k for k in card.get("results", {}) if k not in card.get("enabled", [])]
        if others:
            st.markdown(f"**{L(_STATIC[25])}**")
            for k in others:
                m = card["results"][k]
                reason = (_STATIC[26] if m.get("excluded_by_design")
                          else _STATIC[27] if m["roc_auc"] < 0.70 or m["pr_auc"] < 1.5 * m["prevalence"] else _STATIC[28])
                st.markdown(f"- {title(k)}: {L(_STATIC[21])} {m['roc_auc']:.2f}, {L(_STATIC[30])} "
                            f"{m.get('baseline_auc_age_sex', 0):.2f}. {L(_STATIC[29])} {L(reason)}.")
        st.caption(L(_STATIC[31]) + " " + "; ".join(D.get(x, x) for x in card.get("limitations", [])))
