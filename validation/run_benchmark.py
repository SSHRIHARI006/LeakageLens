"""Run the LeakageLens synthetic detector benchmark.

Usage:
    python -m validation.run_benchmark --seeds 10 --output validation/results
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from leakagelens import AuditConfig, LeakageLens
from leakagelens.detectors import exact_duplicates, group_overlap, near_duplicates, suspicious_features, temporal_audit
from validation.generators import FAMILIES, generate

DETECTOR_KEYS = [
    "exact_duplicates.split_contamination",
    "exact_duplicates.label_conflict",
    "group_overlap.group",
    "temporal.temporal",
    "near_duplicates.near_duplicate",
    "feature_suspicion.target_proxy",
    "feature_suspicion.target_association",
]
INFLATION_FAMILIES = {"SYN-00", "SYN-01", "SYN-02", "SYN-03", "SYN-14"}


def _dataset_hash(frame) -> str:
    values = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    return hashlib.sha256(values).hexdigest()


def _commit_sha() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _detect(frame, manifest: dict, key: str) -> tuple[bool, int | None]:
    target = manifest["target"]
    train, test = manifest["train_index"], manifest["test_index"]
    group = "entity" if "entity" in frame.columns else None
    time_column = "event_date" if "event_date" in frame.columns else None
    context = "temporal" if manifest["inference_scenario"] == "future_prediction" else "iid"
    if key == "exact_duplicates.split_contamination":
        findings = exact_duplicates(frame, target, train, test)
        match = [f for f in findings if f.category == "split_contamination"]
        return bool(match), match[0].affected_rows if match else 0
    if key == "exact_duplicates.label_conflict":
        findings = exact_duplicates(frame, target, train, test)
        match = [f for f in findings if f.category == "label_conflict"]
        return bool(match), match[0].affected_rows if match else 0
    if key == "group_overlap.group":
        findings = group_overlap(frame, group, train, test)
        return bool(findings), findings[0].affected_rows if findings else 0
    if key == "temporal.temporal":
        findings = temporal_audit(frame, time_column, train, test, context)
        match = [f for f in findings if f.verification_status == "deterministic" and f.title.startswith("Future")]
        return bool(match), match[0].affected_rows if match else 0
    if key == "near_duplicates.near_duplicate":
        findings = near_duplicates(frame, target)
        return bool(findings), findings[0].affected_rows if findings else 0
    if key == "feature_suspicion.target_proxy":
        findings = suspicious_features(frame, target, manifest["task"])
        return any(f.category == "target_proxy" for f in findings), None
    if key == "feature_suspicion.target_association":
        findings = suspicious_features(frame, target, manifest["task"])
        return any(f.category == "target_association" for f in findings), None
    raise KeyError(key)


def _config_for(family: str, seed: int) -> AuditConfig:
    if family == "SYN-02":
        return AuditConfig(target="target", group_column="entity", seed=seed)
    if family == "SYN-03":
        return AuditConfig(target="target", time_column="event_date", inference_context="temporal", seed=seed)
    if family == "SYN-14":
        return AuditConfig(target="target", time_column="event_date", inference_context="temporal", seed=seed)
    return AuditConfig(target="target", seed=seed)


def _inflation_run(family: str, seed: int) -> dict:
    frame, _ = generate(family, seed)
    config = _config_for(family, seed)
    started = time.perf_counter()
    try:
        result = LeakageLens(config).audit(frame)
    except Exception as exc:  # pragma: no cover - recorded as an error, not a silent pass
        return {"family": family, "seed": seed, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "family": family, "seed": seed, "runtime_seconds": round(time.perf_counter() - started, 4),
        "original_strategy": result.original_evaluation.strategy if result.original_evaluation else None,
        "safer_strategy": result.safer_evaluation.strategy if result.safer_evaluation else None,
        "original_metrics": result.original_evaluation.metrics if result.original_evaluation else {},
        "safer_metrics": result.safer_evaluation.metrics if result.safer_evaluation else {},
        "inflation": result.inflation, "comparison": result.comparison,
        "risk_score": result.risk_score,
    }


def _score(records: list[dict], detector: str) -> dict:
    rows = [r for r in records if r["detector"] == detector]
    tp = sum(1 for r in rows if r["expected"] and r["detected"])
    fn = sum(1 for r in rows if r["expected"] and not r["detected"])
    fp = sum(1 for r in rows if not r["expected"] and r["detected"])
    tn = sum(1 for r in rows if not r["expected"] and not r["detected"])
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    counted = [r for r in rows if r.get("expected_count") is not None]
    count_tp = sum(1 for r in counted if r.get("predicted_count") == r.get("expected_count"))
    runtimes = [r["runtime_ms"] for r in rows]
    return {
        "detector": detector, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "specificity": specificity,
        "false_positive_rate": (fp / (fp + tn)) if fp + tn else None,
        "false_negative_rate": (fn / (fn + tp)) if fn + tp else None,
        "f1": f1, "positive_support": tp + fn, "negative_support": tn + fp,
        "count_accuracy": (count_tp / len(counted)) if counted else None,
        "count_cases": len(counted),
        "mean_runtime_ms": round(statistics.fmean(runtimes), 3) if runtimes else None,
        "errors": sum(1 for r in rows if r.get("error")),
    }


def _multiseed(records: list[dict]) -> dict:
    """Detection-rate distribution per detector across seeds (exact binary outcome)."""
    by_detector: dict[str, list[dict]] = {}
    for record in records:
        by_detector.setdefault(record["detector"], []).append(record)
    out = {}
    for detector, rows in by_detector.items():
        rates = []
        for seed in sorted({r["seed"] for r in rows}):
            seed_rows = [r for r in rows if r["seed"] == seed]
            if seed_rows:
                rates.append(sum(1 for r in seed_rows if r["detected"] == r["expected"]) / len(seed_rows))
        rate = sum(1 for r in rows if r["detected"] == r["expected"]) / len(rows) if rows else None
        out[detector] = {
            "per_seed_accuracy": rates,
            "mean": round(statistics.fmean(rates), 4) if rates else None,
            "std": round(statistics.pstdev(rates), 4) if len(rates) > 1 else 0.0,
            "median": round(statistics.median(rates), 4) if rates else None,
            "q1": round(float(np.percentile(rates, 25)), 4) if rates else None,
            "q3": round(float(np.percentile(rates, 75)), 4) if rates else None,
            "ci95": (round(statistics.fmean(rates) - 1.96 * statistics.pstdev(rates) / np.sqrt(len(rates)), 4),
                     round(statistics.fmean(rates) + 1.96 * statistics.pstdev(rates) / np.sqrt(len(rates)), 4)) if len(rates) > 1 else None,
            "samples": len(rows), "seed_count": len(rates), "overall_accuracy": round(rate, 4) if rate is not None else None,
            "ci_method": "normal approximation over per-seed accuracy; not a calibrated probability",
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the LeakageLens synthetic detector benchmark.")
    parser.add_argument("--seeds", type=int, default=10, help="Number of independent seeds (default: 10).")
    parser.add_argument("--output", type=str, default="validation/results", help="Output root directory.")
    parser.add_argument("--families", type=str, default="all", help="Comma-separated family IDs, or 'all'.")
    parser.add_argument("--skip-inflation", action="store_true", help="Skip the original-vs-safer inflation experiments.")
    args = parser.parse_args(argv)
    if args.seeds < 1:
        parser.error("--seeds must be at least 1")
    families = FAMILIES if args.families == "all" else [f.strip() for f in args.families.split(",") if f.strip()]
    unknown = [f for f in families if f not in FAMILIES]
    if unknown:
        parser.error(f"Unknown families: {unknown}")
    seeds = list(range(42, 42 + args.seeds + 1))[:args.seeds]  # includes the canonical 42 seed

    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir = Path(args.output) / run_id
    (run_dir / "manifests").mkdir(parents=True, exist_ok=True)
    records, skipped = [], []
    for family in families:
        if family == "SYN-16":
            skipped.append({"family": family, "reason": "Invalid-input family is covered by unit/integration tests, not the detector benchmark."})
            continue
        for seed in seeds:
            frame, manifest = generate(family, seed)
            manifest["dataset_sha256"] = _dataset_hash(frame)
            (run_dir / "manifests" / f"{manifest['dataset_id']}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            for key in DETECTOR_KEYS:
                if key not in manifest["ground_truth"]:
                    continue
                expected = bool(manifest["ground_truth"][key])
                expected_count = manifest.get("expected_counts", {}).get(key)
                started = time.perf_counter()
                error = None
                try:
                    detected, predicted_count = _detect(frame, manifest, key)
                except Exception as exc:  # pragma: no cover - recorded, not hidden
                    detected, predicted_count, error = False, None, f"{type(exc).__name__}: {exc}"
                records.append({
                    "family": family, "dataset_id": manifest["dataset_id"], "dataset_sha256": manifest["dataset_sha256"],
                    "seed": seed, "detector": key,
                    "expected": expected, "detected": bool(detected), "predicted_count": predicted_count,
                    "expected_count": expected_count, "runtime_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": error,
                })
                print(f"{family} seed={seed} {key}: expected={expected} detected={detected}", file=sys.stderr)

    inflation = [] if args.skip_inflation else [_inflation_run(family, seed) for family in families if family in INFLATION_FAMILIES for seed in seeds]
    detectors = sorted({r["detector"] for r in records})
    summary = {
        "run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(), "commit_sha": _commit_sha(),
        "python": platform.python_version(), "platform": platform.platform(),
        "dependencies": {
            "numpy": np.__version__, "pandas": pd.__version__,
            "scikit_learn": __import__("sklearn").__version__,
        },
        "seeds": seeds, "seed_count": len(seeds), "families": families, "skipped": skipped,
        "detector_config": {"near_duplicate_decimals": 2, "near_duplicate_max_rows": 100000,
                            "feature_mi_threshold": 0.5},
        "detectors": {detector: _score(records, detector) for detector in detectors},
        "multiseed": _multiseed(records),
        "records": records,
        "inflation": inflation,
        "caveats": [
            "Synthetic families are constructed by the same project; they are not an independent benchmark.",
            "Risk thresholds were not tuned on these results; the score is a triage heuristic, not a probability.",
            "Original-vs-safer comparisons with different split strategies change the evaluated population; they are observed protocol differences, not causal leakage inflation.",
            "A skipped family or metric is not a pass.",
        ],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (run_dir / "config.json").write_text(json.dumps({"seeds": seeds, "families": families, "skip_inflation": args.skip_inflation}, indent=2), encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "records": len(records), "detectors": detectors}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
