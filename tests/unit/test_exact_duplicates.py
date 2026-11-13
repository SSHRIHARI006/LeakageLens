"""Exact duplicate and train/test overlap detector tests (spec 5.2)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leakagelens.detectors import exact_duplicates, feature_row_hashes


def _findings(frame, target="target", train=None, test=None):
    return exact_duplicates(frame, target, train, test)


def test_no_duplicates_and_no_overlap():
    frame = pd.DataFrame({"x": [1, 2, 3, 4], "target": [0, 1, 0, 1]})
    assert _findings(frame, train=[0, 1], test=[2, 3]) == []


def test_two_identical_rows_reported():
    frame = pd.DataFrame({"x": [1, 1, 2, 3], "target": [0, 0, 1, 0]})
    findings = _findings(frame)
    assert len(findings) == 1
    assert findings[0].category == "duplicate"
    assert findings[0].affected_rows == 2
    assert findings[0].evidence["duplicate_groups"] == 1
    assert findings[0].verification_status == "deterministic"


def test_three_copies_count_and_groups():
    frame = pd.DataFrame({"x": [1, 1, 1, 2], "target": [0, 0, 0, 1]})
    evidence = _findings(frame)[0].evidence
    assert evidence["duplicate_rows"] == 3
    assert evidence["duplicate_groups"] == 1


def test_conflicting_labels_surface_separately():
    frame = pd.DataFrame({"x": [1, 1, 2, 3], "target": [0, 1, 0, 1]})
    findings = _findings(frame)
    assert [f.category for f in findings] == ["duplicate", "label_conflict"]
    conflict = findings[1]
    assert conflict.evidence["conflicting_groups"] == 1
    assert "not identical labelled examples" in conflict.description


def test_identical_features_different_indices_are_duplicates():
    frame = pd.DataFrame({"x": [5, 6, 5, 7], "target": [0, 1, 0, 1]}, index=[10, 20, 30, 40])
    findings = _findings(frame)
    assert findings and findings[0].evidence["duplicate_rows"] == 2


def test_predictive_duplicates_ignore_identifiers_and_raw_target():
    frame = pd.DataFrame({
        "encounter_id": [101, 202], "patient_nbr": [11, 22], "x": [5, 5],
        "readmitted": ["NO", "<30"], "readmitted_within_30_days": [0, 1],
    })
    findings = exact_duplicates(frame, "readmitted_within_30_days")
    assert findings and findings[0].category == "duplicate"


def test_predictive_duplicate_overlap_ignores_identifiers():
    frame = pd.DataFrame({
        "encounter_id": [101, 202], "patient_nbr": [11, 22], "x": [5, 5],
        "readmitted": ["NO", "<30"], "readmitted_within_30_days": [0, 1],
    })
    findings = exact_duplicates(frame, "readmitted_within_30_days", train=[0], test=[1])
    assert any(f.category == "split_contamination" for f in findings)


def test_split_overlap_counts_test_rows():
    frame = pd.DataFrame({"x": [1, 2, 3, 4, 1, 5], "target": [0, 1, 0, 1, 0, 1]})
    findings = exact_duplicates(frame, "target", train=[0, 1, 2, 3], test=[4, 5])
    overlap = [f for f in findings if f.category == "split_contamination"]
    assert len(overlap) == 1
    assert overlap[0].affected_rows == 1
    assert overlap[0].evidence["test_rows_with_train_match"] == 1


def test_duplicates_within_train_only_have_no_cross_split_finding():
    frame = pd.DataFrame({"x": [1, 1, 2, 3], "target": [0, 0, 1, 0]})
    findings = exact_duplicates(frame, "target", train=[0, 1, 2], test=[3])
    assert any(f.category == "duplicate" for f in findings)
    assert not any(f.category == "split_contamination" for f in findings)


def test_duplicates_within_test_only_have_no_cross_split_finding():
    frame = pd.DataFrame({"x": [1, 2, 3, 3], "target": [0, 0, 1, 0]})
    findings = exact_duplicates(frame, "target", train=[0, 1], test=[2, 3])
    assert not any(f.category == "split_contamination" for f in findings)


def test_empty_split_arrays_do_not_divide_by_zero():
    frame = pd.DataFrame({"x": [1, 2], "target": [0, 1]})
    assert exact_duplicates(frame, "target", train=[], test=[0]) == []
    assert exact_duplicates(frame, "target", train=[0], test=[]) == []


def test_out_of_range_and_non_integer_indices_rejected():
    frame = pd.DataFrame({"x": [1, 2], "target": [0, 1]})
    with pytest.raises(ValueError, match="out of range"):
        exact_duplicates(frame, "target", train=[0, 5], test=[1])
    with pytest.raises(ValueError, match="must be integers"):
        exact_duplicates(frame, "target", train=[0.5], test=[1])


def test_null_does_not_collide_with_missing_sentinel_string():
    frame = pd.DataFrame({"x": ["<MISSING>", None, "other"], "target": [0, 1, 0]})
    hashes = feature_row_hashes(frame.drop(columns=["target"]))
    assert hashes.nunique() == 3


def test_target_is_excluded_from_hashing():
    frame = pd.DataFrame({"x": [1, 1], "target": [0, 1]})
    assert feature_row_hashes(frame.drop(columns=["target"])).nunique() == 1


def test_mixed_dtypes_hash_stably():
    frame = pd.DataFrame({
        "num": [1.5, 1.5], "cat": ["a", "a"], "flag": [True, True],
        "when": pd.to_datetime(["2024-01-01", "2024-01-01"]), "target": [0, 1],
    })
    hashes = feature_row_hashes(frame.drop(columns=["target"]))
    assert hashes.iloc[0] == hashes.iloc[1]
    assert np.issubdtype(hashes.dtype, np.integer)
