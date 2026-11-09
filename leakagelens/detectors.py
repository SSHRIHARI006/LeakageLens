from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Iterable
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
from .schemas import Finding

SUSPICIOUS_TERMS = ("outcome", "diagnosis", "result", "final", "target", "label", "post", "future", "discharge", "status")

def _severity(score: float) -> str:
    return "critical" if score >= 80 else "high" if score >= 55 else "moderate" if score >= 25 else "low"

def exact_duplicates(frame: pd.DataFrame, target: str, train: Iterable[int] | None = None, test: Iterable[int] | None = None) -> list[Finding]:
    features = frame.drop(columns=[target], errors="ignore")
    row_hash = pd.util.hash_pandas_object(features.fillna("<MISSING>"), index=False)
    duplicate_mask = row_hash.duplicated(keep=False)
    groups = int(row_hash[duplicate_mask].nunique())
    count = int(duplicate_mask.sum())
    findings: list[Finding] = []
    if count:
        pct = round(100 * count / len(frame), 2)
        findings.append(Finding("exact_duplicates", "duplicate", _severity(pct), "high", min(90, pct), "Exact duplicate feature rows detected", f"{count} of {len(frame)} rows ({pct}%) share feature values with another row.", {"duplicate_rows": count, "duplicate_groups": groups, "percent_rows": pct}, affected_rows=count, recommendation="Keep each duplicate group in one evaluation partition; do not silently delete rows.", verification_status="deterministic"))
    if train is not None and test is not None:
        overlap = set(row_hash.iloc[list(train)]) & set(row_hash.iloc[list(test)])
        affected = int(row_hash.iloc[list(test)].isin(overlap).sum())
        if affected:
            pct = round(100 * affected / len(test), 2)
            findings.append(Finding("exact_duplicates", "split_contamination", "high" if pct < 30 else "critical", "high", min(100, 50 + pct), "Train/test duplicate overlap", f"{affected} test rows have an exact feature match in training.", {"test_rows_with_train_match": affected, "test_overlap_percent": pct}, affected_rows=affected, recommendation="Use duplicate-group-aware splitting and compare it with the original evaluation.", verification_status="deterministic"))
    return findings

def near_duplicates(frame: pd.DataFrame, target: str, decimals: int = 2, max_rows: int = 100_000) -> list[Finding]:
    """Scalable blocking approximation: rows equal after numeric rounding and categorical normalization."""
    features = frame.drop(columns=[target], errors="ignore")
    sampled = len(features) > max_rows
    work = features.iloc[:max_rows].copy() if sampled else features.copy()
    for column in work.select_dtypes(include=np.number): work[column] = work[column].round(decimals)
    for column in work.select_dtypes(exclude=np.number): work[column] = work[column].astype("string").str.strip().str.lower()
    hashes = pd.util.hash_pandas_object(work.fillna("<MISSING>"), index=False)
    mask = hashes.duplicated(keep=False)
    count = int(mask.sum())
    if not count:
        return []
    pct = round(100 * count / len(work), 2)
    note = f" Analysis was sampled to the first {max_rows} rows." if sampled else ""
    return [Finding("near_duplicates", "near_duplicate", _severity(pct), "medium", min(70, pct), "Approximate near-duplicate candidates", f"{count} rows ({pct}%) match after rounding numeric values to {decimals} decimals and normalizing categorical text.{note}", {"candidate_rows": count, "percent_analyzed_rows": pct, "numeric_round_decimals": decimals, "sampled": sampled, "analyzed_rows": len(work)}, affected_rows=count, recommendation="Review candidates and use appropriate entity/duplicate grouping before interpreting the evaluation.", verification_status="heuristic")]

def group_overlap(frame: pd.DataFrame, group: str | None, train: Iterable[int] | None, test: Iterable[int] | None) -> list[Finding]:
    if not group or train is None or test is None: return []
    groups = frame[group]
    shared = set(groups.iloc[list(train)].dropna()) & set(groups.iloc[list(test)].dropna())
    if not shared: return []
    affected = int(groups.iloc[list(test)].isin(shared).sum())
    pct = round(100 * affected / len(test), 2)
    return [Finding("group_overlap", "group", "high" if pct < 30 else "critical", "high", min(100, 50 + pct), "Declared entity groups cross the split", f"{len(shared)} '{group}' values occur in both partitions.", {"shared_groups": len(shared), "affected_test_rows": affected, "percent_test_rows": pct}, [group], affected, "Use a group-aware split if deployment requires generalization to new entities.", "deterministic")]

def temporal_audit(frame: pd.DataFrame, time: str | None, train: Iterable[int] | None, test: Iterable[int] | None, task_context: str) -> list[Finding]:
    if not time or train is None or test is None or task_context != "temporal": return []
    dates = pd.to_datetime(frame[time], errors="coerce")
    if dates.isna().all():
        return [Finding("temporal", "temporal", "moderate", "high", 35, "Time column could not be parsed", f"'{time}' has no parseable dates.", affected_columns=[time], recommendation="Provide a valid datetime column or select IID prediction.", verification_status="deterministic")]
    future_train = int((dates.iloc[list(train)] > dates.iloc[list(test)].min()).sum())
    if future_train:
        return [Finding("temporal", "temporal", "high", "high", 70, "Future observations appear in training", f"{future_train} training rows occur after the earliest evaluation date.", {"train_max": str(dates.iloc[list(train)].max()), "test_min": str(dates.iloc[list(test)].min())}, [time], future_train, "For future prediction, use chronological splitting with training dates before test dates.", "deterministic")]
    return []

def suspicious_features(frame: pd.DataFrame, target: str, task: str) -> list[Finding]:
    findings = []
    names = [c for c in frame.columns if c != target and any(term in c.lower() for term in SUSPICIOUS_TERMS)]
    if names:
        findings.append(Finding("feature_suspicion", "target_proxy", "moderate", "low", 30, "Potential post-outcome feature names", "Names alone do not establish leakage, but these columns merit domain review.", {"matched_terms": list(SUSPICIOUS_TERMS)}, names, recommendation="Confirm each feature is available at the intended prediction time.", verification_status="heuristic"))
    numeric = frame.drop(columns=[target], errors="ignore").select_dtypes(include=np.number)
    if not numeric.empty:
        x = numeric.fillna(numeric.median()).replace([np.inf, -np.inf], 0)
        y = frame[target]
        try:
            scores = mutual_info_classif(x, y.astype("category").cat.codes, random_state=42) if task == "classification" else mutual_info_regression(x, pd.to_numeric(y), random_state=42)
            top = pd.Series(scores, index=x.columns).sort_values(ascending=False).head(5)
            if float(top.iloc[0]) > 0.8:
                findings.append(Finding("feature_suspicion", "target_association", "moderate", "medium", 35, "Unusually strong numerical target association", "High association can be legitimate and requires domain validation.", {"mutual_information": top.round(4).to_dict()}, [str(top.index[0])], recommendation="Check that the top feature is not target-derived or recorded after the outcome.", verification_status="heuristic"))
        except (ValueError, TypeError): pass
    return findings

def pipeline_audit(pipeline: object | None) -> list[Finding]:
    if pipeline is None: return [Finding("pipeline_audit", "pipeline", "low", "low", 5, "No pipeline supplied", "Dataset-level checks can run, but preprocessing behavior cannot be inspected.", recommendation="Supply a scikit-learn Pipeline for structural inspection.", verification_status="unable_to_determine")]
    name = type(pipeline).__name__
    if not hasattr(pipeline, "fit"):
        return [Finding("pipeline_audit", "pipeline", "moderate", "high", 35, "Unsupported pipeline object", f"{name} is not sklearn-compatible.", recommendation="Use an sklearn-compatible estimator or Pipeline; dataset audits will continue.", verification_status="unable_to_determine")]
    return [Finding("pipeline_audit", "pipeline", "low", "medium", 0, "Pipeline is compatible with fold-local evaluation", f"{name} can be fit only on the training partition by LeakageLens.", recommendation="Keep preprocessing inside the supplied pipeline.", verification_status="verified")]
