"""Exploratory data analysis (EDA) of the NHANES data used by MediLens AI.

Run from the project folder (after train_nhanes_model.py has downloaded the files):
    python eda_nhanes.py
    python eda_nhanes.py --data-dir data/nhanes

It prints each step and saves figures and tables to eda_outputs/ (use them in your report and slides).
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from train_nhanes_model import CYCLES, FEATURES, LABELS, build_cycle

OUT = Path("eda_outputs")
LABS = [n for _v, (n, _u) in FEATURES.items() if n != "age"]
UNITS = {n: u for _v, (n, u) in FEATURES.items()}
SKEWED = ["triglycerides", "alt", "ast", "ggt", "creatinine", "bun", "total_bilirubin", "alk_phos", "wbc", "ldl"]
AGE_BINS = [18, 30, 40, 50, 60, 70, 80, 91]
SHOWCASE = {"diabetes": "hba1c", "kidney_disease": "creatinine", "liver_condition": "alt",
            "gout": "uric_acid", "high_cholesterol": "ldl", "heart_disease": "hdl"}
REPORT = []


def step(title):
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)
    REPORT.append(f"\n## {title}\n")


def show(df, note=""):
    text = df.to_string()
    print(text)
    REPORT.append("```\n" + text + "\n```\n" + (note + "\n" if note else ""))


def save(name):
    plt.tight_layout()
    plt.savefig(OUT / name, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"  saved eda_outputs/{name}")


def load(data_dir):
    frames = [d for y, s in CYCLES if (d := build_cycle(Path(data_dir), y, s, False)) is not None]
    if not frames:
        raise SystemExit("No data found. Run train_nhanes_model.py first, or pass --data-dir.")
    return pd.concat(frames, ignore_index=True)


def main(data_dir):
    OUT.mkdir(exist_ok=True)
    df = load(data_dir)
    labs = [c for c in LABS if c in df.columns]
    labels = [k for k in LABELS if f"y_{k}" in df.columns]

    step("STEP 1. Structure of the data")
    print(f"Adults with lab data: {len(df)} | features: {len(labs) + 1} | conditions: {len(labels)}")
    per_cycle = df.groupby("cycle").agg(adults=("age", "size"), median_age=("age", "median"),
                                         percent_male=("sex_male", lambda s: round(100 * s.mean(), 1)))
    show(per_cycle, "Check that every cycle has a similar size and a similar age and sex mix.")

    step("STEP 2. Data quality: missing values")
    miss = (df[labs].isna().mean() * 100).round(1).sort_values(ascending=False)
    show(miss.to_frame("percent_missing"), "LDL and triglycerides are only measured on a fasting subsample.")
    by_cycle = (df.groupby("cycle")[labs].apply(lambda g: g.isna().mean() * 100).round(0).T)
    show(by_cycle, "A column that is empty in a whole cycle means that test was not measured then.")
    miss.to_csv(OUT / "missingness.csv")
    plt.figure(figsize=(8, 7))
    plt.barh(miss.index[::-1], miss.values[::-1], color="#2E86C1")
    plt.xlabel("% missing")
    plt.title("Missing values per lab")
    save("01_missingness.png")

    step("STEP 3. Data quality: impossible values and units")
    odd = []
    for c in labs:
        s = df[c].dropna()
        odd.append({"feature": c, "unit": UNITS[c], "n": len(s), "negative_or_zero": int((s <= 0).sum()),
                    "min": round(s.min(), 2), "median": round(s.median(), 2), "max": round(s.max(), 2)})
    odd = pd.DataFrame(odd).set_index("feature")
    show(odd, "Zeros in counts or enzymes, or a huge max, are worth checking before modelling.")

    step("STEP 4. One variable at a time: distributions and outliers")
    rows = []
    for c in labs:
        s = df[c].dropna()
        if len(s) < 50:
            continue
        q1, q3 = s.quantile([.25, .75])
        iqr = q3 - q1
        rows.append({"feature": c, "skew": round(s.skew(), 2), "p1": round(s.quantile(.01), 2),
                     "p99": round(s.quantile(.99), 2),
                     "pct_beyond_1.5IQR": round(100 * ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).mean(), 1)})
    dist = pd.DataFrame(rows).set_index("feature").sort_values("skew", ascending=False)
    show(dist, "Skew above 1 means a long right tail. Those labs are better read on a log scale.")
    dist.to_csv(OUT / "distribution_summary.csv")
    key = [c for c in ["hba1c", "glucose", "creatinine", "alt", "uric_acid", "ldl", "triglycerides", "hemoglobin",
                       "wbc", "platelets", "albumin", "total_cholesterol"] if c in df.columns]
    fig, axes = plt.subplots(3, 4, figsize=(14, 8))
    for ax, c in zip(axes.ravel(), key):
        s = df[c].dropna()
        if c in SKEWED:
            s, lab = np.log10(s[s > 0]), f"log10({c})"
        else:
            lab = c
        ax.hist(s, bins=40, color="#2E86C1")
        ax.set_title(f"{c} [{UNITS[c]}]", fontsize=9)
        ax.set_xlabel(lab, fontsize=8)
    save("02_distributions.png")

    step("STEP 5. How common is each condition?")
    prev = pd.DataFrame({k: {"known": int(df[f'y_{k}'].notna().sum()), "cases": int((df[f'y_{k}'] == 1).sum()),
                             "prevalence_%": round(100 * df[f'y_{k}'].mean(), 1)} for k in labels}).T
    show(prev, "Rare conditions (a few percent) are hard to predict. That is why precision is low for them.")
    prev.to_csv(OUT / "label_prevalence.csv")
    pc = pd.DataFrame({k: df.groupby("cycle")[f"y_{k}"].mean() * 100 for k in labels}).round(1)
    show(pc.T, "Prevalence should be fairly stable across cycles. A question not asked in a cycle shows as NaN.")

    step("STEP 6. Age and sex: the biggest confounders")
    df["age_group"] = pd.cut(df["age"], AGE_BINS, right=False)
    age_prev = pd.DataFrame({k: df.groupby("age_group", observed=True)[f"y_{k}"].mean() * 100 for k in labels}).round(1)
    show(age_prev, "Many conditions rise steeply with age, which is why each model is compared with an age + sex baseline.")
    plt.figure(figsize=(9, 6))
    for k in labels:
        plt.plot([str(i.left) for i in age_prev.index], age_prev[k], marker="o", label=LABELS[k][0])
    plt.xlabel("Age group (starting age)")
    plt.ylabel("% with the condition")
    plt.legend(fontsize=7, ncol=2)
    plt.title("Prevalence rises with age")
    save("03_prevalence_by_age.png")
    sex_prev = pd.DataFrame({k: df.groupby("sex_male")[f"y_{k}"].mean() * 100 for k in labels}).round(1)
    sex_prev.index = ["female", "male"]
    show(sex_prev.T, "Percent with each condition, by sex.")

    step("STEP 7. Lab values for people with and without a condition")
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for ax, (k, c) in zip(axes.ravel(), SHOWCASE.items()):
        if k not in labels or c not in df.columns:
            ax.axis("off")
            continue
        d = df[[c, f"y_{k}"]].dropna()
        groups = [d.loc[d[f"y_{k}"] == 0, c], d.loc[d[f"y_{k}"] == 1, c]]
        ax.boxplot(groups, showfliers=False)
        ax.set_xticklabels(["no", "yes"])
        ax.set_title(f"{c} by {LABELS[k][0]}", fontsize=9)
        ax.set_ylabel(UNITS[c])
        if c in SKEWED:
            ax.set_yscale("log")
    save("04_labs_by_condition.png")

    step("STEP 8. Which single lab separates each condition best? (one-variable ROC-AUC)")
    rows = []
    for k in labels:
        for c in labs + ["age"]:
            d = df[[c, f"y_{k}"]].dropna()
            if len(d) < 300 or d[f"y_{k}"].nunique() < 2:
                continue
            auc = roc_auc_score(d[f"y_{k}"], d[c])
            rows.append({"condition": k, "feature": c, "auc": round(max(auc, 1 - auc), 3),
                         "cases_have": "higher values" if auc >= 0.5 else "lower values"})
    uni = pd.DataFrame(rows)
    uni.to_csv(OUT / "univariate_auc.csv", index=False)
    top = uni.sort_values("auc", ascending=False).groupby("condition").head(3).sort_values(["condition", "auc"],
                                                                                           ascending=[True, False])
    show(top.set_index(["condition", "feature"]), "0.5 means no separation, 1.0 is perfect. Age often tops the list.")

    step("STEP 9. Relationships between labs (correlation)")
    corr = df[labs].corr(method="spearman")
    plt.figure(figsize=(11, 9))
    plt.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    plt.colorbar(label="Spearman correlation")
    plt.xticks(range(len(labs)), labs, rotation=90, fontsize=7)
    plt.yticks(range(len(labs)), labs, fontsize=7)
    plt.title("Correlation between lab values")
    save("05_correlation.png")
    pairs = corr.where(np.triu(np.ones(corr.shape), 1).astype(bool)).stack().rename("correlation").reset_index()
    pairs["abs"] = pairs["correlation"].abs()
    strong = pairs.sort_values("abs", ascending=False).head(10).drop(columns="abs").round(2)
    show(strong.set_index(["level_0", "level_1"]), "Strongly correlated labs carry overlapping information (for example AST and ALT).")

    step("STEP 10. Did anything drift between survey cycles?")
    drift_cols = [c for c in ["hba1c", "glucose", "creatinine", "alt", "ast", "uric_acid", "ldl", "hemoglobin"]
                  if c in df.columns]
    drift = df.groupby("cycle")[drift_cols].median().round(2)
    show(drift, "Big jumps in a median between cycles can mean a change in lab method, not in people.")
    fig, axes = plt.subplots(2, 4, figsize=(14, 6))
    for ax, c in zip(axes.ravel(), drift_cols):
        ax.plot(drift.index, drift[c], marker="o", color="#2E86C1")
        ax.set_title(c, fontsize=9)
    save("06_median_by_cycle.png")

    (OUT / "EDA_REPORT.md").write_text("# EDA of the NHANES data\n" + "\n".join(REPORT), encoding="utf-8")
    print("\nDone. Tables and figures are in eda_outputs/ (EDA_REPORT.md has every table in one file).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/nhanes")
    main(ap.parse_args().data_dir)
