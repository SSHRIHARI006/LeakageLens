"""Heuristic suspicious-feature tests (spec 5.6)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leakagelens.detectors import suspicious_features


def test_suspicious_name_warns_with_low_confidence():
    frame = pd.DataFrame({"final_status": [0, 1, 0, 1], "x": [1.0, 2.0, 3.0, 4.0], "target": [0, 1, 0, 1]})
    findings = suspicious_features(frame, "target", "classification")
    proxy = [f for f in findings if f.category == "target_proxy"]
    assert proxy and proxy[0].confidence == "low"
    assert "proof" not in proxy[0].description.lower() or "not" in proxy[0].description.lower()


def test_ordinary_names_do_not_trigger_name_warning():
    frame = pd.DataFrame({"age": [30, 40, 50, 60], "spend": [1.0, 2.0, 3.0, 4.0], "target": [0, 1, 0, 1]})
    assert not any(f.category == "target_proxy" for f in suspicious_features(frame, "target", "classification"))


def test_high_mutual_information_is_reported_as_heuristic():
    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    frame = pd.DataFrame({"legit": x, "noise": rng.normal(size=200), "target": (x > 0).astype(int)})
    findings = suspicious_features(frame, "target", "classification")
    association = [f for f in findings if f.category == "target_association"]
    assert association
    assert association[0].verification_status == "heuristic"
    assert "legitimate" in association[0].description.lower()


def test_direct_target_copy_is_flagged_by_name_or_association():
    rng = np.random.default_rng(1)
    target = rng.integers(0, 2, 100)
    frame = pd.DataFrame({"x": rng.normal(size=100), "target_copy": target, "target": target})
    findings = suspicious_features(frame, "target", "classification")
    assert any(f.category in {"target_proxy", "target_association"} for f in findings)


def test_regression_and_multiclass_and_string_labels_run():
    rng = np.random.default_rng(2)
    x = rng.normal(size=80)
    regression = pd.DataFrame({"x": x, "target": x * 3 + rng.normal(0, .1, 80)})
    assert isinstance(suspicious_features(regression, "target", "regression"), list)
    multiclass = pd.DataFrame({"x": x, "target": rng.integers(0, 3, 80)})
    assert isinstance(suspicious_features(multiclass, "target", "classification"), list)
    strings = pd.DataFrame({"x": x, "target": np.where(x > 0, "yes", "no")})
    assert isinstance(suspicious_features(strings, "target", "classification"), list)


def test_all_null_and_infinite_numeric_features_do_not_crash():
    frame = pd.DataFrame({
        "all_null": [np.nan] * 20,
        "inf": [np.inf, -np.inf] * 10,
        "constant": [1.0] * 20,
        "target": [0, 1] * 10,
    })
    suspicious_features(frame, "target", "classification")


def test_categorical_only_dataset_reports_coverage():
    frame = pd.DataFrame({"cat": ["a", "b"] * 20, "target": [0, 1] * 20})
    findings = suspicious_features(frame, "target", "classification")
    coverage = [f for f in findings if f.category == "coverage"]
    assert coverage
    assert coverage[0].verification_status == "unable_to_determine"
    assert coverage[0].evidence["skipped_columns"] == ["cat"]
