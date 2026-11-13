"""Multi-seed stability tests (spec 9.2)."""
from __future__ import annotations

import statistics

from leakagelens.detectors import exact_duplicates, group_overlap, near_duplicates, temporal_audit
from validation.run_benchmark import _multiseed
from validation.generators import generate

SEEDS = [42, 43, 44]


def _detect(family: str, seed: int) -> dict[str, bool]:
    frame, manifest = generate(family, seed)
    target = manifest["target"]
    train, test = manifest["train_index"], manifest["test_index"]
    duplicates = exact_duplicates(frame, target, train, test)
    return {
        "split": any(f.category == "split_contamination" for f in duplicates),
        "group": bool(group_overlap(frame, "entity" if "entity" in frame.columns else None, train, test)),
        "temporal": any(
            f.verification_status == "deterministic" and f.title.startswith("Future")
            for f in temporal_audit(
                frame,
                "event_date" if "event_date" in frame.columns else None,
                train,
                test,
                "temporal" if manifest["inference_scenario"] == "future_prediction" else "iid",
            )
        ),
        "near": bool(near_duplicates(frame, target)),
    }


def test_split_contamination_detected_across_seeds():
    assert all(_detect("SYN-01", seed)["split"] for seed in SEEDS)


def test_group_overlap_detected_across_seeds():
    assert all(_detect("SYN-02", seed)["group"] for seed in SEEDS)


def test_temporal_contamination_detected_across_seeds():
    assert all(_detect("SYN-03", seed)["temporal"] for seed in SEEDS)


def test_near_duplicates_detected_across_seeds():
    assert all(_detect("SYN-06", seed)["near"] for seed in SEEDS)


def test_clean_family_negative_across_seeds():
    for seed in SEEDS:
        detected = _detect("SYN-00", seed)
        assert not any(detected.values())


def test_multiseed_statistics_are_reported_with_ci_and_caveat():
    records = []
    for seed in SEEDS:
        for detected, expected in ((True, True), (True, True), (False, False)):
            records.append({"detector": "d", "seed": seed, "detected": detected, "expected": expected, "runtime_ms": 1.0, "error": None})
    stats = _multiseed(records)["d"]
    assert stats["seed_count"] == 3
    assert stats["samples"] == 9
    assert stats["mean"] == 1.0
    assert stats["ci95"] is not None
    assert "not a calibrated probability" in stats["ci_method"]
    assert statistics.pstdev(stats["per_seed_accuracy"]) == 0
