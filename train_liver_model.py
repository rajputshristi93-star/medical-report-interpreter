"""Train and evaluate a liver-disease SCREENING model on the Indian Liver Patient Dataset (ILPD).

Run from the project folder:
    pip install scikit-learn joblib matplotlib ucimlrepo
    python train_liver_model.py                      (downloads the data from UCI)
    python train_liver_model.py --csv data/ilpd.csv  (uses a local copy instead)

Outputs: models/liver_model.joblib, models/liver_model.json (model card), models/liver_*.png
This is an educational model. It is NOT a diagnostic tool.
"""
import argparse
import json
import os
from datetime import date

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, brier_score_loss,
                             classification_report, confusion_matrix, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

SEED = 42
FEATURES = ["age", "sex_male", "total_bilirubin", "direct_bilirubin", "alk_phos",
            "alt", "ast", "total_protein", "albumin", "ag_ratio"]
LOG_COLS = ["total_bilirubin", "direct_bilirubin", "alk_phos", "alt", "ast"]  # right-skewed
UNITS = {"age": "years", "sex_male": "1=male, 0=female", "total_bilirubin": "mg/dL",
         "direct_bilirubin": "mg/dL", "alk_phos": "U/L", "alt": "U/L", "ast": "U/L",
         "total_protein": "g/dL", "albumin": "g/dL", "ag_ratio": "ratio"}


def load_data(csv_path):
    """Returns X (DataFrame with FEATURES) and y (1 = liver patient, 0 = not)."""
    if csv_path:
        raw = pd.read_csv(csv_path, header=None)
        raw = raw.iloc[1:] if str(raw.iloc[0, 0]).strip().lower() in ("age", "a") else raw
    else:
        from ucimlrepo import fetch_ucirepo
        d = fetch_ucirepo(id=225)  # ILPD
        raw = pd.concat([d.data.features, d.data.targets], axis=1)
    raw = raw.iloc[:, :11].copy()  # the file has 10 features and the class in the last column
    raw.columns = ["age", "gender", "total_bilirubin", "direct_bilirubin", "alk_phos", "alt",
                   "ast", "total_protein", "albumin", "ag_ratio", "label"]
    raw["sex_male"] = raw["gender"].astype(str).str.strip().str.lower().str.startswith("m").astype(int)
    for c in FEATURES[:1] + FEATURES[2:] + ["label"]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw = raw.dropna(subset=["label"])
    y = (raw["label"] == 1).astype(int)  # in ILPD, 1 = liver patient, 2 = not
    return raw[FEATURES], y


def make_pipeline(model):
    log = Pipeline([("imp", SimpleImputer(strategy="median")),
                    ("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one"))])
    plain = SimpleImputer(strategy="median")
    other = [c for c in FEATURES if c not in LOG_COLS]
    pre = ColumnTransformer([("log", log, LOG_COLS), ("num", plain, other)])
    return Pipeline([("pre", pre), ("scale", StandardScaler()), ("model", model)])


def candidates():
    return {
        "baseline (always majority class)": DummyClassifier(strategy="most_frequent"),
        "logistic regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                                class_weight="balanced_subsample", random_state=SEED),
        "gradient boosting": GradientBoostingClassifier(random_state=SEED),
    }


def main(csv_path):
    X, y = load_data(csv_path)
    print(f"Rows: {len(X)} | liver patients: {int(y.sum())} | not: {int((1 - y).sum())}")
    print(f"Accuracy of always guessing 'liver patient': {y.mean():.1%}  <- the number to beat\n")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    scoring = {"roc_auc": "roc_auc", "pr_auc": "average_precision",
               "recall": "recall", "balanced_acc": "balanced_accuracy"}

    print("5-fold cross-validation on the training set (mean of folds)")
    rows, best_name, best_auc = [], None, -1
    for name, model in candidates().items():
        s = cross_validate(make_pipeline(model), X_tr, y_tr, cv=cv, scoring=scoring)
        r = {k: s[f"test_{k}"].mean() for k in scoring}
        rows.append((name, r))
        print(f"  {name:34} ROC-AUC {r['roc_auc']:.3f} | PR-AUC {r['pr_auc']:.3f} | "
              f"recall {r['recall']:.3f} | balanced acc {r['balanced_acc']:.3f}")
        if not name.startswith("baseline") and r["roc_auc"] > best_auc:
            best_name, best_auc = name, r["roc_auc"]

    print(f"\nBest by cross-validated ROC-AUC: {best_name}")
    pipe = make_pipeline(candidates()[best_name]).fit(X_tr, y_tr)
    proba = pipe.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {"roc_auc": roc_auc_score(y_te, proba), "pr_auc": average_precision_score(y_te, proba),
               "recall": recall_score(y_te, pred), "balanced_accuracy": balanced_accuracy_score(y_te, pred),
               "brier_score": brier_score_loss(y_te, proba)}
    print("\nHeld-out test set (never used for choosing the model)")
    for k, v in metrics.items():
        print(f"  {k:18} {v:.3f}")
    print("\nConfusion matrix [rows = truth (not, liver), columns = prediction]")
    print(confusion_matrix(y_te, pred))
    print("\n" + classification_report(y_te, pred, target_names=["not liver patient", "liver patient"]))

    print("Check by sex (the dataset is 3/4 male, so models can be less reliable for women)")
    by_sex = {}
    for label, flag in (("male", 1), ("female", 0)):
        m = (X_te["sex_male"] == flag).values
        if m.sum() > 5 and len(set(y_te[m])) > 1:
            by_sex[label] = {"n": int(m.sum()), "recall": float(recall_score(y_te[m], pred[m])),
                             "roc_auc": float(roc_auc_score(y_te[m], proba[m]))}
            print(f"  {label:7} n={m.sum():3}  recall {by_sex[label]['recall']:.3f}  "
                  f"ROC-AUC {by_sex[label]['roc_auc']:.3f}")

    os.makedirs("models", exist_ok=True)
    joblib.dump(pipe, "models/liver_model.joblib")
    card = {
        "name": "Liver disease screening model (educational)",
        "trained_on": str(date.today()), "sklearn_version": sklearn.__version__,
        "algorithm": best_name, "threshold": 0.5, "features": FEATURES, "units": UNITS,
        "dataset": "Indian Liver Patient Dataset (ILPD), UCI repository, 583 records "
                   "from north-east Andhra Pradesh, India",
        "class_balance": {"liver_patient": int(y.sum()), "not_liver_patient": int((1 - y).sum())},
        "baseline_accuracy_majority_class": float(y.mean()),
        "cv_results": {n: {k: float(v) for k, v in r.items()} for n, r in rows},
        "test_metrics": {k: float(v) for k, v in metrics.items()}, "test_by_sex": by_sex,
        "limitations": ["Small dataset from one region", "Labels are clinical diagnoses, not proven ground truth",
                        "Not validated on other labs, assays or populations",
                        "Screening aid only. Not a diagnosis."],
    }
    with open("models/liver_model.json", "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)
    print("\nSaved models/liver_model.joblib and models/liver_model.json")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay
        RocCurveDisplay.from_predictions(y_te, proba, name=best_name)
        plt.plot([0, 1], [0, 1], "--", color="grey")
        plt.title("ROC curve (test set)")
        plt.savefig("models/liver_roc.png", dpi=150, bbox_inches="tight")
        plt.close()
        ConfusionMatrixDisplay.from_predictions(y_te, pred, display_labels=["not liver", "liver"])
        plt.title("Confusion matrix (test set)")
        plt.savefig("models/liver_confusion.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("Saved models/liver_roc.png and models/liver_confusion.png (use them in your report)")
    except Exception as e:  # plots are optional
        print("Plots skipped:", e)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="path to a local ILPD csv (UCI format, no header)")
    main(ap.parse_args().csv)
