"""Deterministic synthetic dataset generators with separated ground-truth manifests.

Each generator returns ``(frame, manifest)``. The manifest is evaluation metadata:
it is never passed to a detector or model. Split indices in the manifest are
positional and are the only split information the benchmark evaluator uses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FAMILIES = [
    "SYN-00", "SYN-01", "SYN-02", "SYN-03", "SYN-04", "SYN-05", "SYN-06", "SYN-07", "SYN-08",
    "SYN-09", "SYN-10", "SYN-11", "SYN-12", "SYN-13", "SYN-14", "SYN-15", "SYN-16",
]


def _base_frame(seed: int, n: int = 160, task: str = "classification", labels=("no", "yes")):
    rng = np.random.default_rng(seed)
    # Keep ordinary benchmark rows distinct; duplicate/rounding behavior is
    # planted explicitly in SYN-01/SYN-06 rather than arising by collision.
    age = rng.normal(45, 12, n).round(6)
    spend = rng.normal(100, 30, n).round(6)
    segment = rng.choice(["A", "B", "C"], n)
    signal = age * .05 + spend * .02 + rng.normal(0, 1, n)
    if task == "regression":
        target = (signal * 10).round(2)
    else:
        raw = (signal > np.median(signal)).astype(int)
        target = np.where(raw == 1, labels[1], labels[0])
    return pd.DataFrame({"age": age, "spend": spend, "segment": segment, "target": target}), rng


def _manifest(family: str, seed: int, task: str, target: str, frame: pd.DataFrame, train, test, *, mechanism: str, expected: dict, scenario: str, notes: str = "", extra: dict | None = None) -> dict:
    manifest = {
        "dataset_id": f"{family.lower()}_seed_{seed}",
        "family": family,
        "seed": seed,
        "task": task,
        "target": target,
        "planted_mechanism": mechanism,
        "affected_row_ids": [str(i) for i in (extra or {}).get("affected_row_ids", [])],
        "affected_columns": (extra or {}).get("affected_columns", []),
        "expected_detector_categories": (extra or {}).get("expected_detector_categories", []),
        "expected_severity_floor": (extra or {}).get("expected_severity_floor", None),
        "inference_scenario": scenario,
        "train_index": [int(i) for i in train],
        "test_index": [int(i) for i in test],
        "ground_truth": expected,
        "expected_counts": (extra or {}).get("expected_counts", {}),
        "notes": notes or "Ground-truth metadata is for evaluator use only.",
    }
    return manifest


def _random_split(n: int, seed: int, test_fraction: float = .25):
    rng = np.random.default_rng(seed + 991)
    order = rng.permutation(n)
    cut = max(1, int(n * (1 - test_fraction)))
    return order[:cut].tolist(), order[cut:].tolist()


CLEAN_KEYS = {
    "exact_duplicates.split_contamination": False,
    "exact_duplicates.label_conflict": False,
    "group_overlap.group": False,
    "temporal.temporal": False,
    "near_duplicates.near_duplicate": False,
    "feature_suspicion.target_proxy": False,
}


def generate(family: str, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    if family == "SYN-00":
        frame, _ = _base_frame(seed)
        train, test = _random_split(len(frame), seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="none", expected=dict(CLEAN_KEYS), scenario="iid_or_group_generalization")
    if family == "SYN-01":
        frame, _ = _base_frame(seed, 120)
        copies = frame.iloc[:30].copy()
        frame = pd.concat([frame, copies], ignore_index=True)
        train = list(range(0, 120)); test = list(range(120, 150))
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="exact_duplicate_overlap",
            expected={**CLEAN_KEYS, "exact_duplicates.split_contamination": True, "exact_duplicates.label_conflict": False, "near_duplicates.near_duplicate": True},
            scenario="iid_or_group_generalization",
            extra={"affected_row_ids": list(range(120, 150)), "affected_columns": ["age", "spend", "segment"],
                   "expected_detector_categories": ["exact_duplicates"], "expected_severity_floor": "high",
                   "expected_counts": {"exact_duplicates.split_contamination": 30}})
    if family == "SYN-02":
        rng = np.random.default_rng(seed)
        n_train, n_test = 180, 60
        entity = np.concatenate([np.arange(n_train) % 40, np.arange(n_test) % 40])
        frame = pd.DataFrame({
            "x": rng.normal(size=n_train + n_test).round(6),
            "entity": entity,
            "target": rng.integers(0, 2, n_train + n_test),
        })
        train, test = list(range(n_train)), list(range(n_train, n_train + n_test))
        shared = set(frame["entity"].iloc[train]) & set(frame["entity"].iloc[test])
        affected = int(frame["entity"].iloc[test].isin(shared).sum())
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="group_overlap",
            expected={**CLEAN_KEYS, "group_overlap.group": True},
            scenario="iid_or_group_generalization",
            extra={"affected_row_ids": frame.index[frame["entity"].isin(shared)].tolist(), "affected_columns": ["entity"],
                   "expected_detector_categories": ["group_overlap"], "expected_severity_floor": "high",
                   "expected_counts": {"group_overlap.group": affected}})
    if family == "SYN-03":
        frame, _ = _base_frame(seed, 160)
        frame["event_date"] = pd.date_range("2023-01-01", periods=len(frame), freq="D")
        train = list(range(40, 160)); test = list(range(0, 40))
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="future_in_train",
            expected={**CLEAN_KEYS, "temporal.temporal": True},
            scenario="future_prediction",
            extra={"affected_row_ids": list(range(40, 160)), "affected_columns": ["event_date"],
                   "expected_detector_categories": ["temporal"], "expected_severity_floor": "high",
                   "expected_counts": {"temporal.temporal": 120}})
    if family == "SYN-04":
        frame, _ = _base_frame(seed, 160)
        frame["final_status"] = frame["target"].map({"no": 0, "yes": 1})
        train, test = _random_split(len(frame), seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="target_copy",
            expected={**CLEAN_KEYS, "feature_suspicion.target_proxy": True},
            scenario="iid_or_group_generalization",
            extra={"affected_columns": ["final_status"], "expected_detector_categories": ["feature_suspicion"],
                   "expected_severity_floor": "moderate", "notes": "Name/most-association warnings are heuristic, not proof."})
    if family == "SYN-05":
        rng = np.random.default_rng(seed)
        n = 160
        legit = rng.normal(size=n).round(2)
        target = (legit * 10 + rng.normal(0, .5, n)).round(2)
        frame = pd.DataFrame({"legit_signal": legit, "noise": rng.normal(size=n).round(2), "target": target})
        train, test = _random_split(n, seed)
        return frame, _manifest(family, seed, "regression", "target", frame, train, test,
            mechanism="none_strong_legitimate_predictor",
            expected={**CLEAN_KEYS, "feature_suspicion.target_proxy": False},
            scenario="iid_or_group_generalization",
            extra={"affected_columns": ["legit_signal"], "notes": "Legitimate strong predictor; any warning is a measured false positive."})
    if family in {"SYN-06", "SYN-07"}:
        rng = np.random.default_rng(seed)
        n = 120
        if family == "SYN-06":
            offsets = np.tile(np.linspace(0.0001, 0.003, n // 4), 4)
            frame = pd.DataFrame({
                "x": np.repeat([1.001, 2.004, 3.001, 4.002], n // 4) + offsets,
                "z": np.repeat([0.111, 0.222, 0.333, 0.444], n // 4) + offsets,
                "target": rng.integers(0, 2, n),
            })
            expected = True
        else:
            frame = pd.DataFrame({
                "x": np.repeat([1.0, 2.1, 3.2, 4.3], n // 4),
                "z": np.arange(n) * 0.37,
                "target": rng.integers(0, 2, n),
            })
            expected = False
        train, test = _random_split(n, seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="rounding_candidates" if expected else "none",
            expected={**CLEAN_KEYS, "near_duplicates.near_duplicate": expected},
            scenario="iid_or_group_generalization",
            extra={"affected_columns": ["x"], "expected_counts": {"near_duplicates.near_duplicate": n if expected and family == "SYN-06" else 0}})
    if family == "SYN-08":
        rng = np.random.default_rng(seed)
        n = 120
        frame = pd.DataFrame({
            "x": rng.normal(size=n).round(3), "constant": 1.0, "all_null": np.nan,
            "mixed": [f"v{i}" for i in range(n)], "target": rng.integers(0, 2, n),
        })
        frame.loc[::7, "x"] = np.nan
        train, test = _random_split(n, seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="none", expected=dict(CLEAN_KEYS), scenario="iid_or_group_generalization",
            extra={"affected_columns": ["constant", "all_null"]})
    if family == "SYN-09":
        frame, _ = _base_frame(seed, 160, task="regression")
        train, test = _random_split(len(frame), seed)
        return frame, _manifest(family, seed, "regression", "target", frame, train, test,
            mechanism="none", expected=dict(CLEAN_KEYS), scenario="iid_or_group_generalization")
    if family == "SYN-10":
        frame, rng = _base_frame(seed, 180)
        frame["target"] = rng.integers(0, 3, len(frame))
        train, test = _random_split(len(frame), seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="none", expected=dict(CLEAN_KEYS), scenario="iid_or_group_generalization")
    if family == "SYN-11":
        frame, _ = _base_frame(seed, 160, labels=("yes", "no"))
        train, test = _random_split(len(frame), seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="none", expected=dict(CLEAN_KEYS), scenario="iid_or_group_generalization",
            notes="String binary labels stress metric encoding, not leakage.")
    if family == "SYN-12":
        frame, _ = _base_frame(seed, 120)
        copies = frame.iloc[:20].copy()
        copies["target"] = copies["target"].map({"no": "yes", "yes": "no"})
        frame = pd.concat([frame, copies], ignore_index=True)
        train, test = _random_split(len(frame), seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="conflicting_labels_for_identical_features",
            expected={**CLEAN_KEYS, "exact_duplicates.split_contamination": True,
                      "exact_duplicates.label_conflict": True, "near_duplicates.near_duplicate": True},
            scenario="iid_or_group_generalization",
            extra={"affected_row_ids": list(range(120, 140)), "affected_columns": ["age", "spend", "segment"],
                   "expected_detector_categories": ["exact_duplicates"], "expected_severity_floor": "moderate"})
    if family == "SYN-13":
        rng = np.random.default_rng(seed)
        n = 120
        frame = pd.DataFrame({"x": rng.normal(size=n).round(2), "entity": np.arange(n), "target": rng.integers(0, 2, n)})
        train, test = _random_split(n, seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="none", expected=dict(CLEAN_KEYS), scenario="iid_or_group_generalization")
    if family == "SYN-14":
        frame, _ = _base_frame(seed, 160)
        frame["event_date"] = pd.date_range("2023-01-01", periods=len(frame), freq="D")
        train = list(range(0, 120)); test = list(range(120, 160))
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="none", expected={**CLEAN_KEYS, "temporal.temporal": False}, scenario="future_prediction")
    if family == "SYN-15":
        frame, _ = _base_frame(seed, 160)
        frame["event_date"] = pd.date_range("2023-01-01", periods=len(frame), freq="D")
        train, test = _random_split(len(frame), seed)
        return frame, _manifest(family, seed, "classification", "target", frame, train, test,
            mechanism="none", expected=dict(CLEAN_KEYS), scenario="iid",
            notes="Date column present but inference scenario is IID; no temporal warning expected.")
    if family == "SYN-16":
        raise ValueError("SYN-16 covers invalid inputs and is exercised by unit/integration tests instead of the detector benchmark.")
    raise ValueError(f"Unknown synthetic family '{family}'.")


def manifest_for(family: str, seed: int = 42) -> dict:
    _, manifest = generate(family, seed)
    return manifest
