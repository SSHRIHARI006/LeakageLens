from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression

from .schemas import Finding

SUSPICIOUS_TERMS = ("outcome", "diagnosis", "result", "final", "target", "label", "post", "future", "discharge", "status")
NULL_TOKEN = "<MISSING>"


def _severity(score: float) -> str:
    return "critical" if score >= 80 else "high" if score >= 55 else "moderate" if score >= 25 else "low"


def _as_indices(values: Iterable[int] | None, n_rows: int, label: str) -> np.ndarray | None:
    """Validate a positional index array used by split-based detectors."""
    if values is None:
        return None
    array = np.asarray(list(values))
    if array.size == 0:
        return array.astype(int)
    if array.dtype.kind not in "iu":
        raise ValueError(f"{label} indices must be integers.")
    if array.max(initial=-1) >= n_rows or array.min(initial=0) < 0:
        raise ValueError(f"{label} indices are out of range for {n_rows} rows.")
    return array.astype(int)


def feature_row_hashes(features: pd.DataFrame) -> pd.Series:
    """Stable per-row fingerprint for exact duplicate matching.

    Nulls use a separate null-pattern column so a real string equal to the null
    token cannot collide with an actual missing value.
    """
    keys = features.astype(object).where(features.notna(), NULL_TOKEN)
    null_pattern = features.isna().apply(lambda column: "".join("1" if v else "0" for v in column), axis=1)
    keys = keys.copy()
    keys["__null_pattern__"] = null_pattern
    return pd.util.hash_pandas_object(keys, index=False)


def exact_duplicates(frame: pd.DataFrame, target: str, train: Iterable[int] | None = None, test: Iterable[int] | None = None) -> list[Finding]:
    """Detect exact duplicate feature rows and train/test feature overlap."""
    features = frame.drop(columns=[target], errors="ignore")
    row_hash = feature_row_hashes(features)
    duplicate_mask = row_hash.duplicated(keep=False)
    groups = int(row_hash[duplicate_mask].nunique())
    count = int(duplicate_mask.sum())
    findings: list[Finding] = []
    if count:
        pct = round(100 * count / len(frame), 2)
        findings.append(Finding("exact_duplicates", "duplicate", _severity(pct), "high", min(90, pct),
            "Exact duplicate feature rows detected",
            f"{count} of {len(frame)} rows ({pct}%) share feature values with another row.",
            {"duplicate_rows": count, "duplicate_groups": groups, "percent_rows": pct},
            affected_rows=count,
            recommendation="Keep each duplicate group in one evaluation partition; do not silently delete rows.",
            verification_status="deterministic"))
        if target in frame:
            conflicts = frame.loc[duplicate_mask].groupby(row_hash[duplicate_mask].to_numpy())[target].nunique()
            conflict_groups = int((conflicts > 1).sum())
            if conflict_groups:
                conflict_rows = int(duplicate_mask.sum())
                findings.append(Finding("exact_duplicates", "label_conflict", "moderate", "high", 40,
                    "Duplicate feature rows have conflicting target labels",
                    f"{conflict_groups} duplicate feature group(s) contain more than one target label, so copies are not identical labelled examples.",
                    {"conflicting_groups": conflict_groups, "rows_in_duplicate_groups": conflict_rows},
                    affected_rows=conflict_rows,
                    recommendation="Inspect label conflicts; do not treat conflicting copies as harmless identical examples.",
                    verification_status="deterministic"))
    train_idx = _as_indices(train, len(frame), "train")
    test_idx = _as_indices(test, len(frame), "test")
    if train_idx is not None and test_idx is not None:
        if test_idx.size and train_idx.size:
            overlap = set(row_hash.iloc[train_idx].tolist()) & set(row_hash.iloc[test_idx].tolist())
            affected = int(row_hash.iloc[test_idx].isin(overlap).sum())
        else:
            affected = 0
        if affected:
            pct = round(100 * affected / len(test_idx), 2)
            findings.append(Finding("exact_duplicates", "split_contamination", "high" if pct < 30 else "critical", "high", min(100, 50 + pct),
                "Train/test duplicate overlap",
                f"{affected} test rows have an exact feature match in training.",
                {"test_rows_with_train_match": affected, "test_overlap_percent": pct},
                affected_rows=affected,
                recommendation="Use duplicate-group-aware splitting and compare it with the original evaluation.",
                verification_status="deterministic"))
    return findings


def near_duplicates(frame: pd.DataFrame, target: str, decimals: int = 2, max_rows: int = 100_000) -> list[Finding]:
    """Blocking approximation: rows equal after numeric rounding and categorical normalization.

    This is deliberately *not* general nearest-neighbour similarity search. It uses
    rounded/normalized row equality and reports only candidates.
    """
    features = frame.drop(columns=[target], errors="ignore")
    sampled = len(features) > max_rows
    work = features.iloc[:max_rows].copy() if sampled else features.copy()
    for column in work.select_dtypes(include=np.number):
        work[column] = work[column].round(decimals)
    for column in work.select_dtypes(exclude=np.number):
        if work[column].dtype == object:
            unhashable = work[column].map(lambda v: isinstance(v, (list, dict, set, bytearray)))
            if unhashable.any():
                raise ValueError(
                    f"Column '{column}' contains unhashable values that cannot be normalized for near-duplicate checks."
                )
        try:
            work[column] = work[column].astype("string").str.strip().str.lower()
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Column '{column}' contains unhashable values that cannot be normalized for near-duplicate checks.") from exc
    hashes = pd.util.hash_pandas_object(work.fillna(NULL_TOKEN), index=False)
    mask = hashes.duplicated(keep=False)
    count = int(mask.sum())
    if not count:
        return []
    pct = round(100 * count / len(work), 2)
    note = f" Analysis was sampled to the first {max_rows} rows." if sampled else ""
    return [Finding("near_duplicates", "near_duplicate", _severity(pct), "medium", min(70, pct),
        "Approximate near-duplicate candidates",
        f"{count} rows ({pct}%) are equal after numeric values are rounded to {decimals} decimals and categorical text is normalized.{note}",
        {"candidate_rows": count, "percent_analyzed_rows": pct, "numeric_round_decimals": decimals, "sampled": sampled, "analyzed_rows": int(len(work))},
        affected_rows=count,
        recommendation="Review candidates and use appropriate entity/duplicate grouping before interpreting the evaluation.",
        verification_status="heuristic")]


def group_overlap(frame: pd.DataFrame, group: str | None, train: Iterable[int] | None, test: Iterable[int] | None) -> list[Finding]:
    """Report entity values present in both partitions; null group IDs are excluded."""
    if not group or train is None or test is None:
        return []
    if group not in frame:
        raise ValueError(f"Group column '{group}' was not found.")
    train_idx = _as_indices(train, len(frame), "train")
    test_idx = _as_indices(test, len(frame), "test")
    groups = frame[group]
    try:
        shared = set(groups.iloc[train_idx].dropna().tolist()) & set(groups.iloc[test_idx].dropna().tolist())
    except TypeError as exc:
        raise ValueError(f"Group column '{group}' contains unhashable values.") from exc
    if not shared:
        return []
    affected = int(groups.iloc[test_idx].isin(shared).sum())
    pct = round(100 * affected / len(test_idx), 2) if len(test_idx) else 0.0
    return [Finding("group_overlap", "group", "high" if pct < 30 else "critical", "high", min(100, 50 + pct),
        "Declared entity groups cross the split",
        f"{len(shared)} '{group}' values occur in both partitions.",
        {"shared_groups": len(shared), "affected_test_rows": affected, "percent_test_rows": pct},
        [str(group)], affected,
        "Use a group-aware split if deployment requires generalization to new entities.",
        "deterministic")]


def temporal_audit(frame: pd.DataFrame, time: str | None, train: Iterable[int] | None, test: Iterable[int] | None, task_context: str) -> list[Finding]:
    """Check future-in-train contamination only when temporal inference is declared."""
    if not time or train is None or test is None or task_context != "temporal":
        return []
    if time not in frame:
        raise ValueError(f"Time column '{time}' was not found.")
    train_idx = _as_indices(train, len(frame), "train")
    test_idx = _as_indices(test, len(frame), "test")
    if not len(train_idx) or not len(test_idx):
        return []
    dates = pd.to_datetime(frame[time], errors="coerce")
    findings: list[Finding] = []
    if dates.isna().all():
        return [Finding("temporal", "temporal", "moderate", "high", 35, "Time column could not be parsed",
            f"'{time}' has no parseable dates.", {"invalid_rows": int(len(dates))}, [str(time)],
            recommendation="Provide a valid datetime column or select IID prediction.",
            verification_status="deterministic")]
    invalid = int(dates.isna().sum())
    if invalid:
        findings.append(Finding("temporal", "temporal", "low", "medium", 10, "Some timestamps could not be parsed",
            f"{invalid} row(s) have unparseable timestamps and were excluded from the chronology comparison.",
            {"invalid_rows": invalid}, [str(time)], invalid,
            recommendation="Fix or remove invalid timestamps before relying on a temporal split.",
            verification_status="deterministic"))
    train_dates = dates.iloc[train_idx]
    test_dates = dates.iloc[test_idx]
    if train_dates.notna().sum() and test_dates.notna().sum():
        test_min = test_dates.min()
        future_train = int((train_dates > test_min).sum())
        if future_train:
            findings.append(Finding("temporal", "temporal", "high", "high", 70, "Future observations appear in training",
                f"{future_train} training rows occur after the earliest evaluation date.",
                {"train_max": str(train_dates.max()), "test_min": str(test_min), "future_train_rows": future_train},
                [str(time)], future_train,
                recommendation="For future prediction, use chronological splitting with training dates before test dates.",
                verification_status="deterministic"))
        elif train_dates.min() == test_dates.max() == train_dates.max():
            findings.append(Finding("temporal", "temporal", "low", "low", 5, "Chronology could not be established",
                "All parsed timestamps are equal, so a temporal ordering violation cannot be determined.",
                {"timestamp": str(train_dates.min())}, [str(time)], None,
                recommendation="Confirm the time column and inference scenario.",
                verification_status="unable_to_determine"))
    return findings


def suspicious_features(frame: pd.DataFrame, target: str, task: str) -> list[Finding]:
    """Heuristic feature-name and numerical target-association warnings.

    Never proof of leakage: both signals are association/name-based and require
    domain validation. Only numeric predictors enter the MI screen; coverage is
    recorded in evidence.
    """
    findings: list[Finding] = []
    names = [c for c in frame.columns if c != target and isinstance(c, str) and any(term in c.lower() for term in SUSPICIOUS_TERMS)]
    if names:
        findings.append(Finding("feature_suspicion", "target_proxy", "moderate", "low", 30, "Potential post-outcome feature names",
            "Names alone do not establish leakage, but these columns merit domain review.",
            {"matched_terms": [term for term in SUSPICIOUS_TERMS if any(term in n.lower() for n in names)], "matched_columns": names},
            list(names), recommendation="Confirm each feature is available at the intended prediction time.",
            verification_status="heuristic"))
    numeric = frame.drop(columns=[target], errors="ignore").select_dtypes(include=np.number)
    skipped = [str(c) for c in frame.columns if c != target and c not in numeric.columns]
    if numeric.empty:
        findings.append(Finding("feature_suspicion", "coverage", "low", "low", 0, "Categorical predictors were not screened",
            "The association screen currently analyzes numeric predictors only; name-based checks still ran.",
            {"analyzed_columns": [], "skipped_columns": skipped}, skipped,
            recommendation="Inspect categorical predictors manually or add them to a domain review.",
            verification_status="unable_to_determine"))
        return findings
    x = numeric.fillna(numeric.median(numeric_only=True)).fillna(0).replace([np.inf, -np.inf], 0)
    y = frame[target]
    try:
        if task == "classification":
            codes = pd.Series(y).astype("category").cat.codes
            scores = mutual_info_classif(x, codes, random_state=42)
        else:
            scores = mutual_info_regression(x, pd.to_numeric(y, errors="coerce").astype(float), random_state=42)
        top = pd.Series(scores, index=x.columns).sort_values(ascending=False).head(5)
        if len(top) and float(top.iloc[0]) > 0.5:
            findings.append(Finding("feature_suspicion", "target_association", "moderate", "medium", 35, "Unusually strong numerical target association",
                "High association can be legitimate and requires domain validation.",
                {"mutual_information": {str(k): round(float(v), 4) for k, v in top.items()}, "analyzed_columns": [str(c) for c in x.columns], "skipped_columns": skipped},
                [str(top.index[0])], recommendation="Check that the top feature is not target-derived or recorded after the outcome.",
                verification_status="heuristic"))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return findings


def pipeline_audit(pipeline: object | None) -> list[Finding]:
    """Compatibility check: can the object be cloned and fit/predict by LeakageLens?

    This is not a static audit of historical preprocessing that happened before
    the data was uploaded.
    """
    if pipeline is None:
        return [Finding("pipeline_audit", "pipeline", "low", "low", 5, "No pipeline supplied",
            "Dataset-level checks can run, but preprocessing behavior cannot be inspected.",
            recommendation="Supply a scikit-learn Pipeline for structural inspection.",
            verification_status="unable_to_determine")]
    name = type(pipeline).__name__
    if not hasattr(pipeline, "fit") or not hasattr(pipeline, "predict"):
        return [Finding("pipeline_audit", "pipeline", "moderate", "high", 35, "Unsupported pipeline object",
            f"{name} must provide both .fit and .predict for fold-local evaluation.",
            {"has_fit": hasattr(pipeline, "fit"), "has_predict": hasattr(pipeline, "predict")},
            recommendation="Use an sklearn-compatible estimator or Pipeline; dataset audits will continue.",
            verification_status="unable_to_determine")]
    return [Finding("pipeline_audit", "pipeline", "low", "medium", 0, "Pipeline is compatible with fold-local evaluation",
        f"{name} can be fit only on the training partition by LeakageLens.",
        {"has_fit": True, "has_predict": True},
        recommendation="Keep preprocessing inside the supplied pipeline.",
        verification_status="verified")]
