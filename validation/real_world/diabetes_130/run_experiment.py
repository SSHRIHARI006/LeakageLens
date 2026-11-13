from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from leakagelens.detectors import exact_duplicates, feature_row_hashes, group_overlap, near_duplicates, suspicious_features
from leakagelens.evaluation import make_split

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = ROOT / "diabetes+130-us+hospitals+for+years+1999-2008" / "diabetic_data.csv"
SEEDS = list(range(42, 52))
TARGET_RAW = "readmitted"
TARGET = "readmitted_within_30_days"
ID_COLUMNS = ["encounter_id", "patient_nbr"]
ADMISSION_EXCLUDE = {
    "discharge_disposition_id", "time_in_hospital", "num_lab_procedures", "num_procedures", "num_medications",
    "max_glu_serum", "A1Cresult", "change", "diabetesMed",
    "metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride", "acetohexamide", "glipizide",
    "glyburide", "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose", "miglitol", "troglitazone",
    "tolazamide", "examide", "citoglipton", "insulin", "glyburide-metformin", "glipizide-metformin",
    "glimepiride-pioglitazone", "metformin-rosiglitazone", "metformin-pioglitazone",
    "diag_2", "diag_3", "number_diagnoses",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dependency_versions() -> dict[str, str]:
    versions = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__}
    for module in ("fastapi", "httpx", "openpyxl", "xlrd", "pytest", "streamlit", "ruff", "pyarrow"):
        try:
            imported = __import__(module)
            versions[module] = getattr(imported, "__version__", "installed")
        except Exception:
            versions[module] = "unavailable"
    return versions


def git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    frame = frame.replace("?", np.nan)
    frame[TARGET] = (frame[TARGET_RAW] == "<30").astype(int)
    return frame


def feature_columns(frame: pd.DataFrame, scenario: str, identifiers: str = "exclude") -> list[str]:
    excluded = {TARGET_RAW, TARGET}
    if identifiers in {"exclude", "encounter"}:
        excluded.add("patient_nbr")
    if identifiers in {"exclude", "patient"}:
        excluded.add("encounter_id")
    if scenario == "admission":
        excluded |= ADMISSION_EXCLUDE
    return [c for c in frame.columns if c not in excluded]


def model_pipeline(frame: pd.DataFrame, features: list[str], name: str, seed: int) -> Pipeline:
    x = frame[features]
    nums = x.select_dtypes(include=np.number).columns.tolist()
    cats = [c for c in features if c not in nums]
    if name in {"dummy", "logistic"}:
        transformers = []
        if nums:
            steps = [("imputer", SimpleImputer(strategy="median"))]
            if name == "logistic":
                steps.append(("scale", StandardScaler()))
            transformers.append(("num", Pipeline(steps), nums))
        if cats:
            transformers.append(("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
            ]), cats))
        pre = ColumnTransformer(transformers)
        estimator = DummyClassifier(strategy="prior") if name == "dummy" else LogisticRegression(max_iter=250, class_weight="balanced", solver="liblinear", random_state=seed)
    else:
        transformers = []
        if nums:
            transformers.append(("num", SimpleImputer(strategy="median"), nums))
        if cats:
            transformers.append(("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encode", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
            ]), cats))
        pre = ColumnTransformer(transformers)
        if name == "tree":
            estimator = DecisionTreeClassifier(max_depth=12, min_samples_leaf=10, class_weight="balanced", random_state=seed)
        elif name == "forest":
            estimator = RandomForestClassifier(n_estimators=80, max_depth=18, min_samples_leaf=4, class_weight="balanced_subsample", n_jobs=-1, random_state=seed)
        else:
            estimator = HistGradientBoostingClassifier(max_iter=120, learning_rate=.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=seed)
    return Pipeline([("preprocessor", pre), ("model", estimator)])


def scores(y_true: pd.Series, pred: np.ndarray, prob: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, prob)) if len(np.unique(y_true)) == 2 else None,
        "average_precision": float(average_precision_score(y_true, prob)),
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
    }


def evaluate(frame: pd.DataFrame, scenario: str, protocol: str, seed: int, model: str, identifiers: str = "exclude") -> dict:
    features = feature_columns(frame, scenario, identifiers)
    if protocol == "random":
        train, test = make_split(frame, TARGET, "classification", seed, strategy="random")
    else:
        train, test = make_split(frame, TARGET, "classification", seed, group="patient_nbr", strategy="group")
    pipe = model_pipeline(frame, features, model, seed)
    t0 = time.perf_counter()
    pipe.fit(frame.iloc[train][features], frame.iloc[train][TARGET])
    fit_s = time.perf_counter() - t0
    pred = pipe.predict(frame.iloc[test][features])
    if hasattr(pipe, "predict_proba"):
        prob = pipe.predict_proba(frame.iloc[test][features])[:, 1]
    else:
        prob = pipe.decision_function(frame.iloc[test][features])
    result = scores(frame.iloc[test][TARGET], pred, prob)
    train_groups = set(frame.iloc[train]["patient_nbr"].dropna().tolist())
    test_groups = set(frame.iloc[test]["patient_nbr"].dropna().tolist())
    result.update({"scenario": scenario, "protocol": protocol, "seed": seed, "model": model, "identifiers": identifiers,
                   "features": len(features), "train_rows": len(train), "test_rows": len(test), "train_patients": len(train_groups),
                   "test_patients": len(test_groups), "patient_overlap": len(train_groups & test_groups), "fit_seconds": fit_s})
    return result


def duplicate_summary(frame: pd.DataFrame, seeds: list[int]) -> dict:
    scenarios = {}
    for scenario in ["admission", "discharge"]:
        features = feature_columns(frame, scenario)
        analysis = frame[features + [TARGET]].copy()
        h = feature_row_hashes(analysis.drop(columns=[TARGET]))
        dup = h.duplicated(keep=False)
        exact = {"rows": int(dup.sum()), "groups": int(h[dup].nunique()), "conflicting_groups": int((analysis.loc[dup].groupby(h[dup].to_numpy())[TARGET].nunique() > 1).sum())}
        random = []
        for seed in seeds:
            train, test = make_split(frame, TARGET, "classification", seed, strategy="random")
            overlap = set(h.iloc[train]) & set(h.iloc[test])
            exact_findings = exact_duplicates(analysis, TARGET, train, test)
            random.append({"seed": seed, "test_rows_with_train_match": int(h.iloc[test].isin(overlap).sum()), "patient_overlap": int(len(set(frame.iloc[train].patient_nbr) & set(frame.iloc[test].patient_nbr))), "detector_split_contamination": any(x.category == "split_contamination" for x in exact_findings)})
        scenarios[scenario] = {"feature_count": len(features), "features": features, "exact_feature_duplicates": exact, "near_duplicates": [x.to_dict() for x in near_duplicates(analysis, TARGET, decimals=2, max_rows=100000)], "random_split_overlap": random}
    return {"scenarios": scenarios, "suspicious_features": [x.to_dict() for x in suspicious_features(frame, TARGET, "classification")]}


def controlled_validation(frame: pd.DataFrame, seed: int = 42) -> list[dict]:
    base = frame.copy()
    train, test = make_split(base, TARGET, "classification", seed, strategy="random")
    cases = []
    # Independent detector labels: clean control, exact feature duplicate, target-derived feature, group overlap.
    clean = exact_duplicates(base, TARGET, train, test)
    cases.append({"condition": "clean_control", "expected": False, "detected": bool(clean), "findings": [x.category for x in clean]})
    injected = base.iloc[[train[0]]].copy()
    injected.index = [len(base)]
    exact = pd.concat([base, injected], ignore_index=True)
    tr2 = np.array(train, dtype=int); te2 = np.array(list(test) + [len(exact) - 1], dtype=int)
    findings = exact_duplicates(exact, TARGET, tr2, te2)
    cases.append({"condition": "exact_duplicate_cross_split", "expected": True, "detected": any(x.category == "split_contamination" for x in findings), "findings": [x.category for x in findings]})
    target_proxy = base.drop(columns=["readmitted"]).copy()
    target_proxy["known_target_proxy"] = target_proxy[TARGET]
    findings = suspicious_features(target_proxy, TARGET, "classification")
    cases.append({"condition": "target_derived_feature", "expected": True, "detected": any(x.category == "target_proxy" for x in findings), "findings": [x.category for x in findings]})
    findings = group_overlap(base, "patient_nbr", train, test)
    cases.append({"condition": "random_patient_group_overlap", "expected": True, "detected": any(x.category == "group" for x in findings), "findings": [x.category for x in findings]})
    grouped_train, grouped_test = make_split(base, TARGET, "classification", seed, group="patient_nbr", strategy="group")
    findings = group_overlap(base, "patient_nbr", grouped_train, grouped_test)
    cases.append({"condition": "grouped_clean_control", "expected": False, "detected": bool(findings), "findings": [x.category for x in findings]})
    return cases


def metadata(frame: pd.DataFrame, path: Path) -> dict:
    counts = frame[TARGET_RAW].value_counts(dropna=False).to_dict()
    patient_counts = frame.groupby("patient_nbr", dropna=False).size()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size, "rows": len(frame), "columns": len(frame.columns),
            "column_names": list(frame.columns), "dtypes": {k: str(v) for k, v in frame.dtypes.items()}, "missing_question_mark_replaced": True,
            "target_raw_counts": {str(k): int(v) for k, v in counts.items()}, "target_positive_rate": float(frame[TARGET].mean()),
            "unique_patients": int(frame.patient_nbr.nunique()), "unique_encounters": int(frame.encounter_id.nunique()), "patients_multiple_encounters": int((patient_counts > 1).sum()),
            "max_encounters_per_patient": int(patient_counts.max()), "mean_encounters_per_patient": float(patient_counts.mean()),
            "full_duplicate_rows": int(frame.drop(columns=[TARGET]).duplicated(keep=False).sum()), "ids": ID_COLUMNS,
            "temporal_fields": [c for c in frame.columns if any(t in c.lower() for t in ["date", "time", "year", "admit"])],
            "target_definition": "1 when readmitted == '<30'; 0 for '>30' or 'NO'."}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--output", type=Path, default=ROOT / "validation" / "real_world" / "diabetes_130" / "results")
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()
    out = args.output / time.strftime("run_%Y%m%dT%H%M%SZ", time.gmtime())
    out.mkdir(parents=True, exist_ok=True)
    frame = load(args.data)
    seeds = SEEDS[:args.seeds]
    (out / "dataset_metadata.json").write_text(json.dumps(metadata(frame, args.data), indent=2))
    config = {"seeds": seeds, "scenarios": {"admission": sorted(ADMISSION_EXCLUDE), "discharge": "all non-target, non-identifier columns"}, "models": ["dummy", "logistic", "tree", "forest", "hist_gradient_boosting"], "protocols": ["random", "patient_grouped"], "identifiers_primary": "excluded", "near_duplicate_decimals": 2, "git_sha": git_sha(), "experiment_script_sha256": sha256(Path(__file__)), "dependency_versions": dependency_versions()}
    (out / "config.json").write_text(json.dumps(config, indent=2))
    (out / "duplicate_and_detector_summary.json").write_text(json.dumps(duplicate_summary(frame, seeds), indent=2, default=str))
    (out / "controlled_validation.json").write_text(json.dumps(controlled_validation(frame), indent=2))
    results = []
    for scenario in ["admission", "discharge"]:
        for protocol in ["random", "patient_grouped"]:
            for model in config["models"]:
                for seed in seeds:
                    t0 = time.perf_counter()
                    try:
                        results.append(evaluate(frame, scenario, protocol, seed, model))
                    except Exception as exc:
                        results.append({"scenario": scenario, "protocol": protocol, "seed": seed, "model": model, "error": repr(exc)})
                    print(f"{scenario} {protocol} {model} seed={seed} elapsed={time.perf_counter()-t0:.1f}s", flush=True)
    pd.DataFrame(results).to_csv(out / "model_results.csv", index=False)
    clean = pd.DataFrame([r for r in results if "error" not in r])
    agg = []
    metric_cols = ["accuracy", "balanced_accuracy", "precision", "recall", "f1", "roc_auc", "average_precision", "specificity", "patient_overlap", "fit_seconds"]
    for keys, group in clean.groupby(["scenario", "protocol", "model"]):
        row = dict(zip(["scenario", "protocol", "model"], keys))
        for col in metric_cols:
            if col in group:
                row[col + "_mean"] = float(group[col].mean())
                row[col + "_sd"] = float(group[col].std(ddof=1))
                row[col + "_min"] = float(group[col].min())
                row[col + "_max"] = float(group[col].max())
        agg.append(row)
    pd.DataFrame(agg).to_csv(out / "model_summary.csv", index=False)
    (out / "run_metadata.json").write_text(json.dumps({"git_sha": git_sha(), "experiment_script_sha256": sha256(Path(__file__)), "dependency_versions": dependency_versions(), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=2))
    print(f"RESULT_DIR={out}", flush=True)


if __name__ == "__main__":
    main()
