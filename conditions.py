"""Rule-based pattern flags for MediLens AI.

Many conditions are DEFINED by lab cutoffs (diabetes range, anemia, kidney stage, thyroid pattern...).
For those, simple clinical rules are more accurate than machine learning, so this module uses rules.
Wording is always 'pattern' or 'range', never 'you have'. Cutoffs follow common clinical guidance
(for example ADA, KDIGO, WHO); have a doctor review them before real users rely on this.
"""
import re

from ml_risk import GDL, MG, MMOL, S, _find, _to_standard, SPECS

EXTRA = {
    "tsh": [S("TSH", "mIU/L", r"^tsh|thyroid stimulating|thyrotropin", ("miu/l", "mlu/l", "µiu/ml", "uiu/ml",
                                                                         "µu/ml", "uu/ml", "miu/ml"), (0.001, 500))],
    "ft4": [S("Free T4", "ng/dL", r"free\s*t4|^ft4|\bft4\b|free thyroxine|thyroxine,?\s*free", ("ng/dl",),
              (0.1, 10), {"pmol/l": 0.0777})],
    "egfr": [S("eGFR", "mL/min/1.73m2", r"egfr|estimated gfr|^gfr", ("ml/min/1.73m2", "ml/min/1.73m²", "ml/min"),
               (1, 200))],
    "ferritin": [S("Ferritin", "ng/mL", r"ferritin", ("ng/ml", "µg/l", "ug/l"), (1, 5000))],
    "vitd": [S("Vitamin D", "ng/mL", r"vitamin d|25-oh|25 oh", ("ng/ml",), (1, 300), {"nmol/l": 0.4006})],
    "b12": [S("Vitamin B12", "pg/mL", r"b12|b-12|cobalamin", ("pg/ml", "ng/l"), (50, 5000), {"pmol/l": 1.355})],
    "esr": [S("ESR", "mm/hr", r"^esr|sedimentation rate", ("mm/hr", "mm/h", "mm/1sthour"), (0, 200))],
    "crp": [S("CRP", "mg/L", r"c-?\s*reactive|^crp", ("mg/l",), (0, 500), {"mg/dl": 10})],
    "neut_pct": [S("Neutrophils %", "%", r"^neutrophils?(\s*%)?$|^neutrophils?\s*\(%\)", ("%",), (0, 100))],
    "lymph_pct": [S("Lymphocytes %", "%", r"^lymphocytes?(\s*%)?$|^lymphocytes?\s*\(%\)", ("%",), (0, 100))],
    "eos_pct": [S("Eosinophils %", "%", r"^eosinophils?(\s*%)?$|^eosinophils?\s*\(%\)", ("%",), (0, 100))],
}


def ckd_epi_2021(scr, age, sex):
    """eGFR in mL/min/1.73m2 from creatinine (mg/dL), age and sex (CKD-EPI 2021 equation)."""
    female = sex == "Female"
    k, a = (0.7, -0.241) if female else (0.9, -0.302)
    return 142 * min(scr / k, 1) ** a * max(scr / k, 1) ** -1.200 * 0.9938 ** age * (1.012 if female else 1)


def _values(results):
    out = {}
    for feat, variants in {**SPECS, **EXTRA}.items():
        found = _find(results, variants)
        if not found:
            continue
        row, spec = found
        v, _why = _to_standard(float(row["value"]), row.get("unit"), spec)
        if v is not None:
            out[feat] = {"v": v, "status": row.get("status"), "name": str(row.get("test", "")), "label": spec["label"],
                         "unit": spec["unit"]}
    return out


def find_patterns(results, age=None, sex=None):
    """Returns a list of dicts: level (urgent | attention | note), title, text, basis."""
    d = _values(results)
    out = []

    def add(level, title, text, *basis):
        out.append({"level": level, "title": title, "text": text,
                    "basis": ", ".join(f"{d[b]['label']} {d[b]['v']:g} {d[b]['unit']}" for b in basis if b in d)})

    val = lambda k: d[k]["v"] if k in d else None
    stat = lambda k: d[k]["status"] if k in d else None
    male, female = sex == "Male", sex == "Female"

    # ---- blood sugar (ADA ranges)
    a1c, glu = val("hba1c"), val("glucose")
    if a1c is not None and a1c >= 6.5:
        add("attention", "Blood sugar: diabetes range",
            "HbA1c of 6.5% or more is in the range doctors use to diagnose diabetes. A doctor confirms it with repeat testing.",
            "hba1c")
    elif a1c is not None and a1c >= 5.7:
        add("note", "Blood sugar: prediabetes range",
            "HbA1c of 5.7 to 6.4% is the prediabetes range. Food, activity and weight changes can bring it down.", "hba1c")
    if glu is not None and re.search(r"fast|fbs", d["glucose"]["name"].lower()):
        if glu >= 126:
            add("attention", "Fasting glucose: diabetes range",
                "A fasting glucose of 126 mg/dL or more is in the diabetes range. A doctor confirms it with repeat testing.",
                "glucose")
        elif glu >= 100:
            add("note", "Fasting glucose: prediabetes range",
                "A fasting glucose of 100 to 125 mg/dL is the prediabetes range.", "glucose")
    if glu is not None and glu < 70:
        add("urgent" if glu < 54 else "attention", "Low blood sugar",
            "Glucose below 70 mg/dL can cause shakiness, sweating and confusion. Tell your doctor, especially if you take "
            "diabetes medicine.", "glucose")

    # ---- kidney stage (KDIGO)
    egfr, est = val("egfr"), False
    if egfr is None and val("creatinine") is not None and age and sex in ("Female", "Male"):
        egfr, est = ckd_epi_2021(val("creatinine"), age, sex), True
    if egfr is not None and (egfr < 60 or (egfr < 90 and (stat("creatinine") == "high" or stat("egfr") == "low"))):
        stage = ("G5 (below 15)" if egfr < 15 else "G4 (15 to 29)" if egfr < 30 else "G3b (30 to 44)" if egfr < 45
                 else "G3a (45 to 59)" if egfr < 60 else "G2 (60 to 89)")
        src = "estimated by this app from creatinine, age and sex" if est else "from your report"
        level = "urgent" if egfr < 15 else "attention" if egfr < 60 else "note"
        text = (f"eGFR {egfr:.0f} ({src}) is in the {stage} range. A value below 60 that lasts 3 months or more is how "
                "chronic kidney disease is defined, so your doctor will usually repeat the test and check urine protein."
                if egfr < 60 else
                f"eGFR {egfr:.0f} ({src}) is slightly reduced (G2). On its own this is common and often not a problem, "
                "unless there are other signs of kidney damage.")
        out.append({"level": level, "title": "Kidney function stage", "text": text,
                    "basis": f"eGFR {egfr:.0f} mL/min/1.73m2" + (" (estimated)" if est else "")})

    # ---- hemoglobin and red cell size
    hb, mcv = val("hemoglobin"), val("mcv")
    low_cut = 13.0 if male else 12.0 if female else None
    if hb is not None and ((low_cut and hb < low_cut) or (not low_cut and stat("hemoglobin") == "low")):
        size = ("The red cells are small, a pattern often seen with iron deficiency or thalassemia trait."
                if mcv is not None and mcv < 80 else
                "The red cells are large, a pattern often seen with low vitamin B12 or folate, thyroid or liver conditions "
                "and some medicines." if mcv is not None and mcv > 100 else
                "The red cells are normal in size, a pattern seen with chronic disease, kidney disease or recent blood loss."
                if mcv is not None else "Red cell size (MCV) was not available, which helps narrow down the cause.")
        fer = val("ferritin")
        extra = " Ferritin is low, which supports iron deficiency." if fer is not None and fer < 30 else ""
        add("urgent" if hb < 7 else "attention" if hb < 11 else "note", "Low hemoglobin (anemia range)",
            f"{size}{extra} The cause needs to be found, so please see a doctor. Do not start iron tablets on your own.",
            "hemoglobin", "mcv", "ferritin")
    high_cut = 16.5 if male else 16.0 if female else None
    if hb is not None and ((high_cut and hb > high_cut) or (not high_cut and stat("hemoglobin") == "high")):
        add("note", "High hemoglobin",
            "Dehydration, smoking and high altitude can raise hemoglobin. If it stays high, a doctor may look further.",
            "hemoglobin")

    # ---- thyroid pattern (uses the report's own ranges)
    ts, ft = stat("tsh"), stat("ft4")
    pattern = {("high", "low"): ("attention", "Thyroid: underactive pattern (overt)",
                                 "High TSH with low free T4 is the pattern seen with an underactive thyroid."),
               ("high", "normal"): ("note", "Thyroid: mildly underactive pattern (subclinical)",
                                    "High TSH with a normal free T4 is called a subclinical underactive pattern. "
                                    "Doctors usually repeat the test."),
               ("low", "high"): ("attention", "Thyroid: overactive pattern (overt)",
                                 "Low TSH with high free T4 is the pattern seen with an overactive thyroid."),
               ("low", "normal"): ("note", "Thyroid: mildly overactive pattern (subclinical)",
                                   "Low TSH with a normal free T4 is called a subclinical overactive pattern. "
                                   "Doctors usually repeat the test.")}.get((ts, ft))
    if pattern:
        add(pattern[0], pattern[1], pattern[2], "tsh", "ft4")
    elif ts in ("high", "low") and ft is None:
        add("note", "Thyroid: TSH outside range",
            "TSH alone cannot show the thyroid pattern. A doctor usually checks free T4 as well.", "tsh")

    # ---- cholesterol (adult categories)
    ldl, tg, hdl = val("ldl"), val("triglycerides"), val("hdl")
    if ldl is not None and ldl >= 160:
        add("attention" if ldl >= 190 else "note", "High LDL cholesterol",
            "LDL of 160 mg/dL or more is high" + (", and 190 or more is very high" if ldl >= 190 else "")
            + ". Heart risk also depends on age, blood pressure, smoking and family history, so ask your doctor.", "ldl")
    if tg is not None and tg >= 200:
        add("attention" if tg >= 500 else "note", "High triglycerides",
            "Triglycerides of 200 mg/dL or more are high." + (" Values of 500 or more can raise the risk of pancreatitis, "
                                                              "so please see a doctor soon." if tg >= 500 else
                                                              " Sugary drinks, refined carbohydrates and alcohol are common causes."),
            "triglycerides")
    hdl_cut = 50 if female else 40
    if hdl is not None and hdl < hdl_cut:
        add("note", "Low HDL cholesterol",
            f"HDL below {hdl_cut} mg/dL is considered low. Exercise and not smoking help raise it.", "hdl")

    # ---- liver patterns
    alt, ast, alp, ggt, bil = val("alt"), val("ast"), val("alk_phos"), val("ggt"), val("total_bilirubin")
    alt_hi, ast_hi = stat("alt") == "high", stat("ast") == "high"
    if (alt is not None and alt >= 1000) or (ast is not None and ast >= 1000):
        add("urgent", "Very high liver enzymes",
            "Liver enzymes at or above 1000 U/L can mean acute liver injury. Please seek medical care promptly.", "alt", "ast")
    elif alt_hi or ast_hi:
        if ast and alt and ast_hi and ast > 2 * alt:
            txt = ("AST is more than twice ALT, a pattern more often seen with alcohol-related liver injury or advanced "
                   "liver disease. Doctors interpret it together with your history.")
        elif alt and ast and alt_hi and alt >= ast:
            txt = ("ALT is raised at least as much as AST, a pattern often seen with fatty liver, viral hepatitis or "
                   "some medicines.")
        else:
            txt = "Liver enzymes are above the range. Medicines, fatty liver and infections are common causes."
        add("attention", "Liver enzyme pattern", txt + " Avoid alcohol until you have spoken to a doctor.", "alt", "ast")
    if stat("alk_phos") == "high" and stat("ggt") == "high":
        add("attention", "Bile flow (cholestatic) pattern",
            "ALP and GGT are both raised, a pattern linked to problems with bile flow. Please discuss with a doctor.",
            "alk_phos", "ggt")
    if bil is not None and stat("total_bilirubin") == "high":
        add("attention" if bil >= 3 else "note", "Raised bilirubin",
            "With normal liver enzymes a mild rise is often harmless (for example Gilbert syndrome), and doctors may "
            "repeat it. A rise with yellow eyes or skin needs prompt review." if not (alt_hi or ast_hi) else
            "Bilirubin is raised together with liver enzymes. Please see a doctor.", "total_bilirubin")
    alb = val("albumin")
    if alb is not None and alb < 3.5:
        add("note", "Low albumin",
            "Low albumin can reflect liver or kidney disease, poor nutrition or inflammation.", "albumin")

    # ---- blood salts
    na, k, ca = val("sodium"), val("potassium"), val("calcium")
    if na is not None and (na < 135 or na > 145):
        add("urgent" if na < 125 or na > 155 else "attention", "Sodium outside range",
            "Sodium affects the brain and muscles. Please see a doctor soon" + (", urgently if you feel confused or very "
                                                                                 "weak" if na < 130 or na > 150 else "") + ".", "sodium")
    if k is not None and (k > 5.0 or k < 3.5):
        add("urgent" if k >= 6.0 or k <= 3.0 else "attention", "Potassium outside range",
            "Potassium affects the heart rhythm. Please see a doctor soon. Do not use salt substitutes or potassium "
            "supplements unless your doctor says so.", "potassium")
    if ca is not None and (ca > 10.5 or ca < 8.5):
        add("urgent" if ca > 12 or ca < 7.5 else "attention", "Calcium outside range",
            "Calcium problems have many causes, including vitamin D, kidney and parathyroid conditions. Please see a doctor.",
            "calcium")

    # ---- white cells, platelets, inflammation
    wbc, plt_ = val("wbc"), val("platelets")
    if wbc is not None and (wbc > 11 or wbc < 4):
        if wbc > 11:
            kind = ("Neutrophils are raised, a pattern often seen with bacterial infection, inflammation or stress."
                    if stat("neut_pct") == "high" else
                    "Lymphocytes are raised, a pattern often seen with viral infections."
                    if stat("lymph_pct") == "high" else
                    "Eosinophils are raised, a pattern often seen with allergies or parasites."
                    if stat("eos_pct") == "high" else "Infection and inflammation are common causes.")
            add("attention" if wbc >= 30 else "note", "High white blood cell count", kind +
                (" A count this high needs prompt medical review." if wbc >= 30 else ""), "wbc", "neut_pct", "lymph_pct")
        else:
            add("urgent" if wbc < 1 else "attention", "Low white blood cell count",
                "Viral infections, some medicines and bone marrow problems can lower white cells. Please see a doctor.", "wbc")
    if plt_ is not None and (plt_ < 150 or plt_ > 450):
        if plt_ < 150:
            add("urgent" if plt_ < 20 else "attention" if plt_ < 100 else "note", "Low platelets",
                "Low platelets can cause easy bruising or bleeding. Get urgent care for bleeding that does not stop.",
                "platelets")
        else:
            add("attention" if plt_ >= 1000 else "note", "High platelets",
                "High platelets often follow infection, inflammation or iron deficiency.", "platelets")
    if stat("esr") == "high" or stat("crp") == "high":
        add("note", "Inflammation marker raised",
            "ESR or CRP is raised. They are general signs of inflammation and do not point to one cause.", "esr", "crp")

    # ---- vitamins, iron, uric acid
    vd, b12, fer = val("vitd"), val("b12"), val("ferritin")
    if vd is not None and vd < 30:
        add("attention" if vd < 20 else "note", "Low vitamin D",
            "Below 20 ng/mL is usually called deficiency and 20 to 29 insufficiency. Ask your doctor about a supplement "
            "and its dose.", "vitd")
    if b12 is not None and b12 < 300:
        add("attention" if b12 < 200 else "note", "Low vitamin B12",
            "Below 200 pg/mL is usually deficiency. Tell your doctor about tingling or numbness. Low B12 is more "
            "common in vegetarians and some medicine users.", "b12")
    if fer is not None and fer < 30 and not (hb is not None and low_cut and hb < low_cut):
        add("note", "Low ferritin",
            "Low ferritin means low iron stores, even before hemoglobin falls. Ask your doctor.", "ferritin")
    ua = val("uric_acid")
    ua_cut = 6.0 if female else 7.0
    if ua is not None and ((sex in ("Female", "Male") and ua > ua_cut) or (sex not in ("Female", "Male") and
                                                                           stat("uric_acid") == "high")):
        add("note", "High uric acid",
            "High uric acid can lead to gout or kidney stones. Alcohol, sugary drinks and red meat can raise it.", "uric_acid")

    order = {"urgent": 0, "attention": 1, "note": 2}
    return sorted(out, key=lambda p: order[p["level"]])


_STATIC = [
    "Patterns doctors look for",
    "Rule-based flags from standard clinical cutoffs. They describe patterns in your values and are not a diagnosis. Only a doctor can tell what your results mean.",
    "Age (optional, for kidney stage and sex-specific cutoffs)", "Biological sex (optional)", "Select", "Female", "Male",
    "Please get medical advice promptly", "Worth discussing with a doctor", "Good to know",
    "None of these rules found a notable pattern in the values that could be read.", "Based on:",
]


def render_patterns_section(embedded=False):
    """Rule-based pattern flags for the results in this session, in the chosen language. Nothing is stored."""
    import html

    import streamlit as st
    from i18n import localize

    results = st.session_state.get("results")
    if not results:
        return
    M = localize(_STATIC)
    L = lambda s: M.get(s, s)
    esc = html.escape
    if not embedded:
        st.divider()
        st.subheader("🔎 " + L(_STATIC[0]))
    st.caption(L(_STATIC[1]))
    c1, c2 = st.columns(2)
    age = c1.number_input(L(_STATIC[2]), min_value=0, max_value=120, value=None, step=1, key="pat_age")
    sex = c2.selectbox(L(_STATIC[3]), ["Select", "Female", "Male"], key="pat_sex", format_func=L)
    patterns = find_patterns(results, age if age and age >= 18 else None, sex)

    if not patterns:
        st.success(L(_STATIC[10]))
        return
    P = localize([x for p in patterns for x in (p["title"], p["text"])])
    for level, cls, heading in (("urgent", "urgent", _STATIC[7]), ("attention", "", _STATIC[8]), ("note", "note", _STATIC[9])):
        group = [p for p in patterns if p["level"] == level]
        if not group:
            continue
        cards = "".join(
            f'<div class="pc {cls}"><b>{esc(P[p["title"]])}</b><p>{esc(P[p["text"]])}</p>'
            + (f'<span class="basis">{esc(L(_STATIC[11]))} {esc(str(p["basis"]))}</span>' if p["basis"] else "") + "</div>"
            for p in group)
        st.markdown(f'<div class="pg-h">{esc(L(heading))}</div><div class="pcs">{cards}</div>', unsafe_allow_html=True)
