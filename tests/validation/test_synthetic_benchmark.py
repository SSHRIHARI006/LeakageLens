"""Synthetic family and benchmark-harness tests (spec 9)."""
from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd
import pytest

from leakagelens.detectors import exact_duplicates, group_overlap, near_duplicates, suspicious_features, temporal_audit
from validation.generators import FAMILIES, generate, manifest_for


@pytest.mark.parametrize("family", [f for f in FAMILIES if f != "SYN-16"])
def test_family_generates_valid_manifest_and_split(family):
    frame, manifest = generate(family, 42)
    assert isinstance(frame, pd.DataFrame) and len(frame) > 0
    assert manifest["family"] == family
    assert manifest["target"] in frame.columns
    assert manifest["ground_truth"], "every benchmark family must declare ground truth"
    train, test = manifest["train_index"], manifest["test_index"]
    assert train and test
    assert set(train).isdisjoint(test)
    assert max(train + test) < len(frame)
    assert sorted(train + test) == list(range(len(frame))), "manifest splits must partition the frame"
    json.dumps(manifest)  # manifests are persisted as JSON


def test_syn_16_is_not_a_detector_benchmark_family():
    with pytest.raises(ValueError, match="invalid inputs"):
        generate("SYN-16", 42)
    with pytest.raises(ValueError, match="Unknown"):
        generate("SYN-99", 42)


def test_ground_truth_is_not_a_frame_column():
    for family in FAMILIES:
        if family == "SYN-16":
            continue
        frame, manifest = generate(family, 42)
        for key in manifest["ground_truth"]:
            assert key not in frame.columns
        assert "ground_truth" not in frame.columns


def test_manifest_for_matches_generate():
    assert manifest_for("SYN-01", 7) == generate("SYN-01", 7)[1]


def test_generation_is_deterministic():
    first = generate("SYN-02", 5)
    second = generate("SYN-02", 5)
    pd.testing.assert_frame_equal(first[0], second[0])
    assert first[1] == second[1]


def _detect(family: str, seed: int = 42):
    frame, manifest = generate(family, seed)
    target = manifest["target"]
    train, test = manifest["train_index"], manifest["test_index"]
    group = "entity" if "entity" in frame.columns else None
    time = "event_date" if "event_date" in frame.columns else None
    context = "temporal" if manifest["inference_scenario"] == "future_prediction" else "iid"
    return {
        "exact_duplicates.split_contamination": any(f.category == "split_contamination" for f in exact_duplicates(frame, target, train, test)),
        "exact_duplicates.label_conflict": any(f.category == "label_conflict" for f in exact_duplicates(frame, target, train, test)),
        "group_overlap.group": bool(group_overlap(frame, group, train, test)),
        "temporal.temporal": any(f.verification_status == "deterministic" and f.title.startswith("Future") for f in temporal_audit(frame, time, train, test, context)),
        "near_duplicates.near_duplicate": bool(near_duplicates(frame, target)),
        "feature_suspicion.target_proxy": any(f.category == "target_proxy" for f in suspicious_features(frame, target, manifest["task"])),
    }, manifest


@pytest.mark.parametrize("family,key", [
    ("SYN-01", "exact_duplicates.split_contamination"),
    ("SYN-01", "near_duplicates.near_duplicate"),
    ("SYN-02", "group_overlap.group"),
    ("SYN-03", "temporal.temporal"),
    ("SYN-04", "feature_suspicion.target_proxy"),
    ("SYN-06", "near_duplicates.near_duplicate"),
    ("SYN-12", "exact_duplicates.label_conflict"),
    ("SYN-13", "group_overlap.group"),
    ("SYN-14", "temporal.temporal"),
    ("SYN-15", "temporal.temporal"),
])
def test_benchmark_detector_matches_declared_ground_truth(family, key):
    detected, manifest = _detect(family)
    assert key in manifest["ground_truth"]
    assert detected[key] is manifest["ground_truth"][key]


def test_expected_counts_match_predicted_counts_for_selected_families():
    detected, manifest = _detect("SYN-01")
    frame, _ = generate("SYN-01", 42)
    findings = exact_duplicates(frame, "target", manifest["train_index"], manifest["test_index"])
    overlap = [f for f in findings if f.category == "split_contamination"][0]
    assert overlap.affected_rows == manifest["expected_counts"]["exact_duplicates.split_contamination"]


def test_benchmark_smoke_writes_real_summary(tmp_path):
    run = subprocess.run(
        [sys.executable, "-m", "validation.run_benchmark", "--seeds", "1", "--families", "SYN-00,SYN-01", "--skip-inflation", "--output", str(tmp_path)],
        capture_output=True, text=True, timeout=600,
    )
    assert run.returncode == 0, run.stderr[-2000:]
    summaries = list(tmp_path.glob("*/summary.json"))
    assert len(summaries) == 1
    summary = json.loads(summaries[0].read_text())
    assert summary["seed_count"] == 1
    assert summary["records"]
    assert not any(r["error"] for r in summary["records"])
    assert summary["detectors"]["exact_duplicates.split_contamination"]["tp"] >= 1
    assert summary["caveats"]
