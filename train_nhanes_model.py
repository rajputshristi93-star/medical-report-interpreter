"""Train multi-condition SCREENING models from NHANES (five survey cycles, 2011 to 2023).

One model per condition. Features = routine lab values + age + sex. Labels = whether the
participant said a doctor told them they have the condition (self-reported).

Honest evaluation:
  * Models are trained on the OLDER cycles and tested on the NEWEST cycle (2021-2023),
    so the test looks like "new people, new year", not a random shuffle.
  * Each model must beat an age + sex only model (many diseases just become more common with age).
  * A condition is ENABLED for the app only if it passes the quality gate below.

Run from the project folder:
    pip install scikit-learn joblib matplotlib pandas numpy
    python train_nhanes_model.py                 (downloads the CDC files to data/nhanes, can take a while)
    python train_nhanes_model.py --no-download   (use the files already in data/nhanes)
Files already downloaded are skipped, so you can stop and run it again.

Outputs: models/nhanes_models.joblib, models/nhanes_model.json, models/nhanes_auc.png
Educational use only. NOT a diagnostic tool.
"""
import argparse
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{name}.xpt"
CYCLES = [("2011", "G"), ("2013", "H"), ("2015", "I"), ("2017", "J"), ("2021", "L")]
TEST_CYCLE = "L"                                # newest cycle: used only for testing
FILES = ["DEMO", "BIOPRO", "CBC", "GHB", "HDL", "TRIGLY", "DIQ", "KIQ_U", "MCQ", "BPQ"]
RECALL_TARGET = 0.80                            # screening: catch at least 80% of cases
GATE_AUC, GATE_LIFT, GATE_MIN_POS = 0.70, 1.5, 30
GATE_LAB_LIFT = 0.10          # labs must beat an age + sex only model by at least this much ROC-AUC
NEVER_ENABLE = {"cancer"}     # ethics: a routine lab report is not a cancer test, so it is never shown to users

# NHANES variable -> (feature name, unit as stored by NHANES)
FEATURES = {
    "RIDAGEYR": ("age", "years"), "LBXHGB": ("hemoglobin", "g/dL"), "LBXHCT": ("hematocrit", "%"),
    "LBXRBCSI": ("rbc", "million/uL"), "LBXWBCSI": ("wbc", "10^3/uL"), "LBXPLTSI": ("platelets", "10^3/uL"),
    "LBXMCVSI": ("mcv", "fL"), "LBXMCHSI": ("mch", "pg"), "LBXMC": ("mchc", "g/dL"), "LBXRDW": ("rdw", "%"),
    "LBXGH": ("hba1c", "%"), "LBXSGL": ("glucose", "mg/dL"), "LBXSCR": ("creatinine", "mg/dL"),
    "LBXSBU": ("bun", "mg/dL"), "LBXSUA": ("uric_acid", "mg/dL"), "LBXSNASI": ("sodium", "mmol/L"),
    "LBXSKSI": ("potassium", "mmol/L"), "LBXSCLSI": ("chloride", "mmol/L"), "LBXSCA": ("calcium", "mg/dL"),
    "LBXSPH": ("phosphorus", "mg/dL"), "LBXSAL": ("albumin", "g/dL"), "LBXSTP": ("total_protein", "g/dL"),
    "LBXSGB": ("globulin", "g/dL"), "LBXSTB": ("total_bilirubin", "mg/dL"), "LBXSATSI": ("alt", "U/L"),
    "LBXSASSI": ("ast", "U/L"), "LBXSAPSI": ("alk_phos", "U/L"), "LBXSGTSI": ("ggt", "U/L"),
    "LBXSCH": ("total_cholesterol", "mg/dL"), "LBXSTR": ("triglycerides", "mg/dL"),
    "LBDHDD": ("hdl", "mg/dL"), "LBDLDL": ("ldl", "mg/dL"),
}

# condition -> (title, questionnaire variables where 1 = yes, 2 = no, key lab features)
# A variable that does not exist in a cycle is simply skipped for that cycle.
LABELS = {
    "diabetes": ("Diabetes", ["DIQ010"], ["hba1c", "glucose"]),
    "kidney_disease": ("Kidney problems", ["KIQ022"], ["creatinine", "bun", "uric_acid"]),
    "kidney_stones": ("Kidney stones", ["KIQ026"], ["calcium", "uric_acid", "creatinine", "phosphorus"]),
    "liver_condition": ("Liver condition", ["MCQ160L"],
                        ["alt", "ast", "alk_phos", "total_bilirubin", "albumin", "ggt"]),
    "gallstones": ("Gallstones", ["MCQ550"], ["total_bilirubin", "alk_phos", "ggt", "total_cholesterol"]),
    "gout": ("Gout", ["MCQ160N"], ["uric_acid", "creatinine"]),
    "high_cholesterol": ("High cholesterol", ["BPQ080"], ["total_cholesterol", "ldl", "triglycerides", "hdl"]),
    "hypertension": ("High blood pressure", ["BPQ020"], ["creatinine", "uric_acid", "triglycerides", "glucose"]),
    "heart_disease": ("Heart disease", ["MCQ160B", "MCQ160C", "MCQ160D", "MCQ160E"],
                      ["ldl", "hdl", "total_cholesterol", "hba1c", "creatinine"]),
    "stroke": ("Stroke", ["MCQ160F"], ["ldl", "hdl", "hba1c", "glucose", "creatinine"]),
    "cancer": ("Cancer (any type)", ["MCQ220"], ["hemoglobin", "wbc", "platelets", "albumin", "alk_phos"]),
}


# ------------------------------------------------------------------ data
def find_file(data_dir, name, suffix):
    for ext in (".xpt", ".XPT", ".csv"):
        p = data_dir / f"{name}_{suffix}{ext}"
        if p.exists():
            return p
    return None


def download(data_dir, name, year, suffix):
    stem = f"{name}_{suffix}"
    url = BASE_URL.format(year=year, name=stem)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            (data_dir / f"{stem}.xpt").write_bytes(urllib.request.urlopen(req, timeout=90).read())
            print(f"  downloaded {stem}")
            return find_file(data_dir, name, suffix)
        except Exception as e:
            print(f"  {stem}: attempt {attempt + 1} failed ({str(e)[:70]})")
            time.sleep(3)
    return None


def read_table(path):
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_sas(path, format="xport", encoding="utf-8")


def label_series(d, variables):
    """1 if any variable is 1 (yes), 0 if all answered 2 (no), otherwise missing."""
    cols = [c for c in variables if c in d.columns]
    if not cols:
        return pd.Series(np.nan, index=d.index)
    yn = pd.concat([d[c].map({1: 1, 2: 0}) for c in cols], axis=1)
    out = pd.Series(np.nan, index=d.index)
    out[(yn == 0).all(axis=1)] = 0
    out[(yn == 1).any(axis=1)] = 1
    return out


def build_cycle(data_dir, year, suffix, allow_download):
    frames = {}
    for name in FILES:
        p = find_file(data_dir, name, suffix) or (download(data_dir, name, year, suffix) if allow_download else None)
        if p is None:
            print(f"  MISSING {name}_{suffix} (skipped)")
            continue
        frames[name] = read_table(p)
    if "DEMO" not in frames:
        print(f"  cycle {suffix}: DEMO file missing, whole cycle skipped")
        return None
    df = frames["DEMO"]
    for name, f in frames.items():
        if name != "DEMO":
            df = df.merge(f.drop(columns=[c for c in f.columns if c in df.columns and c != "SEQN"]),
                          on="SEQN", how="left")
    df = df[df["RIDAGEYR"] >= 18]
    if "RIDEXPRG" in df.columns:
        df = df[df["RIDEXPRG"] != 1]  # pregnancy changes many lab values
    X = pd.DataFrame(index=df.index)
    for var, (name, _unit) in FEATURES.items():
        if var in df.columns:
            X[name] = pd.to_numeric(df[var], errors="coerce")
    X["sex_male"] = (df["RIAGENDR"] == 1).astype(float)
    keep = X.drop(columns=["age", "sex_male"]).notna().sum(axis=1) >= 5  # needs some lab data
    X, df = X[keep], df[keep]
    for key, (_t, variables, _k) in LABELS.items():
        X[f"y_{key}"] = label_series(df, variables)
    X["cycle"] = suffix
    print(f"  cycle {suffix}: {len(X)} adults with lab data")
    return X


# ------------------------------------------------------------------ models
def hgb():
    return HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=300, min_samples_leaf=20,
                                          l2_regularization=1.0, early_stopping=True, n_iter_no_change=20,
                                          random_state=SEED)


def logit():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=2000))


def evaluate_label(full, feats, key):
    d = full[full[f"y_{key}"].notna()]
    y = d[f"y_{key}"].astype(int)
    if y.sum() < 60 or (len(y) - y.sum()) < 60:
        return None
    is_test = (d["cycle"] == TEST_CYCLE).values
    tr_pos, te_pos = int(y[~is_test].sum()), int(y[is_test].sum())
    if te_pos >= GATE_MIN_POS and tr_pos >= 100 and (~is_test).sum() > 500:
        X_tr, y_tr, X_te, y_te = d.loc[~is_test, feats], y[~is_test], d.loc[is_test, feats], y[is_test]
        split = f"train on older cycles, test on {TEST_CYCLE}"
    else:  # not enough cases in the newest cycle: fall back to a random split
        X_tr, X_te, y_tr, y_te = train_test_split(d[feats], y, test_size=0.2, stratify=y, random_state=SEED)
        split = "random 80/20 (too few cases for a time-based split)"

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    cands = {"gradient boosting": hgb(), "logistic regression": logit()}
    cv_auc = {n: float(cross_val_score(m, X_tr, y_tr, cv=cv, scoring="roc_auc").mean()) for n, m in cands.items()}
    best = max(cv_auc, key=cv_auc.get)
    model = cands[best]

    oof = cross_val_predict(model, X_tr, y_tr, cv=cv, method="predict_proba")[:, 1]
    _p, rec, thr_all = precision_recall_curve(y_tr, oof)
    ok = np.where(rec[:-1] >= RECALL_TARGET)[0]
    thr = float(thr_all[ok[-1]]) if len(ok) else 0.5  # highest threshold that still finds 80% of cases

    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    pred = proba >= thr
    pos_te = int(y_te.sum())
    tp = int(((pred == 1) & (y_te.values == 1)).sum())
    prevalence = float(y.mean())
    base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X_tr[["age", "sex_male"]], y_tr)
    base_auc = float(roc_auc_score(y_te, base.predict_proba(X_te[["age", "sex_male"]])[:, 1]))

    m = {"split": split, "rows": int(len(y)), "positives": int(y.sum()), "prevalence": prevalence, "model": best,
         "train_rows": int(len(y_tr)), "test_rows": int(len(y_te)), "test_positives": pos_te,
         "cv_roc_auc": cv_auc, "threshold": thr,
         "roc_auc": float(roc_auc_score(y_te, proba)), "pr_auc": float(average_precision_score(y_te, proba)),
         "recall_at_threshold": tp / max(pos_te, 1), "precision_at_threshold": tp / max(int(pred.sum()), 1),
         "baseline_auc_age_sex": base_auc}
    m["lab_lift"] = m["roc_auc"] - base_auc
    m["enabled"] = bool(m["roc_auc"] >= GATE_AUC and m["pr_auc"] >= GATE_LIFT * float(y_te.mean())
                        and pos_te >= GATE_MIN_POS and m["lab_lift"] >= GATE_LAB_LIFT)
    by_sex = {}
    for name, flag in (("male", 1.0), ("female", 0.0)):
        s = (X_te["sex_male"] == flag).values
        if s.sum() > 30 and len(set(y_te.values[s])) > 1 and y_te.values[s].sum() >= 5:
            by_sex[name] = float(roc_auc_score(y_te.values[s], proba[s]))
    m["roc_auc_by_sex"] = by_sex
    return m, model


def main(data_dir, allow_download):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for year, suffix in CYCLES:
        print(f"NHANES cycle {suffix} (starts {year})")
        d = build_cycle(data_dir, year, suffix, allow_download)
        if d is not None:
            frames.append(d)
    if not frames:
        raise SystemExit("No data found. Put the NHANES files in " + str(data_dir))
    full = pd.concat(frames, ignore_index=True)
    feats = [n for _v, (n, _u) in FEATURES.items() if n in full.columns] + ["sex_male"]
    used = sorted(full["cycle"].unique())
    print(f"\nAdults with lab data: {len(full)} | cycles used: {', '.join(used)} | features: {len(feats)}")
    print(f"Test cycle: {TEST_CYCLE} ({'present' if TEST_CYCLE in used else 'MISSING, random splits will be used'})\n")

    results, models = {}, {}
    print(f"{'condition':18}{'rows':>7}{'cases':>7}{'prev':>7}  {'model':20}{'ROC-AUC':>8}{'age+sex':>8}{'lift':>7}"
          f"{'PR-AUC':>8}{'recall':>8}{'precis.':>8}  status")
    for key in LABELS:
        out = evaluate_label(full, feats, key)
        if out is None:
            print(f"{key:18} too few known cases, skipped")
            continue
        m, model = out
        if key in NEVER_ENABLE:
            m["enabled"], m["excluded_by_design"] = False, True
        results[key], models[key] = m, model
        status = ("excluded by design" if m.get("excluded_by_design")
                  else "ENABLED" if m["enabled"] else "not reliable enough")
        print(f"{key:18}{m['rows']:7}{m['positives']:7}{m['prevalence']:7.1%}  {m['model']:20}"
              f"{m['roc_auc']:8.3f}{m['baseline_auc_age_sex']:8.3f}{m['lab_lift']:7.3f}{m['pr_auc']:8.3f}"
              f"{m['recall_at_threshold']:8.2f}{m['precision_at_threshold']:8.2f}  {status}")
        if m["roc_auc_by_sex"]:
            print(f"{'':18}ROC-AUC by sex: " + ", ".join(f"{k} {v:.3f}" for k, v in m["roc_auc_by_sex"].items())
                  + f"  | {m['split']}")

    enabled = [k for k, m in results.items() if m["enabled"]]
    print(f"\nEnabled for the app: {enabled if enabled else 'none'}")
    print("Quality gate: test ROC-AUC >= 0.70, PR-AUC >= 1.5 x prevalence, >= 30 test cases,")
    print(f"and ROC-AUC at least {GATE_LAB_LIFT:.2f} above a model that only knows age and sex (the 'lift' column).")

    Path("models").mkdir(exist_ok=True)
    joblib.dump({"models": models, "features": feats, "enabled": enabled,
                 "thresholds": {k: m["threshold"] for k, m in results.items()}}, "models/nhanes_models.joblib")
    card = {
        "name": "NHANES multi-condition screening models (educational)", "trained_on": str(date.today()),
        "sklearn_version": sklearn.__version__, "features": feats, "enabled": enabled,
        "titles": {k: LABELS[k][0] for k in results}, "key_features": {k: LABELS[k][2] for k in results},
        "units": {n: u for _v, (n, u) in FEATURES.items()}, "results": results, "cycles_used": used,
        "dataset": f"NHANES survey cycles {', '.join(used)} (US national survey), adults 18+, "
                   f"{len(full)} people; labels are self-reported doctor diagnoses; tested on the newest cycle",
        "limitations": ["US population; may not transfer to other countries, labs or methods",
                        "Self-reported labels, not confirmed diagnoses",
                        "Lab methods changed a little between survey cycles",
                        "Survey sampling weights were not used",
                        "Many conditions become more common with age, so each model is compared with an "
                        "age + sex only baseline and must beat it",
                        "Cancer is evaluated but never shown to users",
                        "Thyroid tests are not included, so no thyroid model",
                        "Screening aid only. Not a diagnosis."],
    }
    with open("models/nhanes_model.json", "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)
    print("Saved models/nhanes_models.joblib and models/nhanes_model.json")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        keys = list(results)
        y = np.arange(len(keys))
        plt.figure(figsize=(7.5, 0.6 * len(keys) + 1.5))
        plt.barh(y + 0.2, [results[k]["roc_auc"] for k in keys], height=0.4, label="with lab values",
                 color=["#2E86C1" if results[k]["enabled"] else "#B0B7BF" for k in keys])
        plt.barh(y - 0.2, [results[k]["baseline_auc_age_sex"] for k in keys], height=0.4, label="age + sex only",
                 color="#E8C46A")
        plt.yticks(y, keys)
        plt.axvline(GATE_AUC, color="red", linestyle="--", label="quality bar (0.70)")
        plt.xlim(0.4, 1.0)
        plt.xlabel("ROC-AUC on the newest survey cycle")
        plt.legend(loc="lower right", fontsize=8)
        plt.title("What lab values add beyond age and sex")
        plt.savefig("models/nhanes_auc.png", dpi=150, bbox_inches="tight")
        print("Saved models/nhanes_auc.png (use it in your report)")
    except Exception as e:
        print("Plot skipped:", e)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/nhanes")
    ap.add_argument("--no-download", action="store_true")
    a = ap.parse_args()
    main(a.data_dir, not a.no_download)
