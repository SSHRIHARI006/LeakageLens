"""Near-duplicate candidate detector tests (spec 5.3).

The detector is a rounding/normalization + row-equality heuristic. These tests
assert that exact contract, not general similarity search.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leakagelens.detectors import near_duplicates


def test_values_equal_after_rounding_are_candidates():
    frame = pd.DataFrame({"x": [1.001, 1.004, 2.5], "target": [0, 1, 0]})
    findings = near_duplicates(frame, "target", decimals=2)
    assert len(findings) == 1
    assert findings[0].affected_rows == 2
    assert findings[0].verification_status == "heuristic"


def test_values_rounding_differently_are_not_candidates():
    frame = pd.DataFrame({"x": [1.0, 1.1, 2.0], "target": [0, 1, 0]})
    assert near_duplicates(frame, "target", decimals=2) == []


def test_categorical_whitespace_and_case_normalized():
    frame = pd.DataFrame({"cat": [" A ", "a"], "target": [0, 1]})
    findings = near_duplicates(frame, "target")
    assert findings and findings[0].affected_rows == 2


def test_target_column_is_excluded():
    frame = pd.DataFrame({"x": [1.0, 1.0], "target": [0, 1]})
    findings = near_duplicates(frame, "target")
    assert findings and findings[0].affected_rows == 2


def test_near_duplicates_ignore_identifiers_and_raw_target():
    frame = pd.DataFrame({
        "encounter_id": [101, 202], "patient_nbr": [11, 22], "x": [1.001, 1.004],
        "readmitted": ["NO", "<30"], "readmitted_within_30_days": [0, 1],
    })
    findings = near_duplicates(frame, "readmitted_within_30_days")
    assert findings and findings[0].affected_rows == 2


def test_max_rows_cap_reports_sampling_and_analyzed_count():
    frame = pd.DataFrame({"x": np.arange(20, dtype=float), "target": [0, 1] * 10})
    # The first ten rows are unique, so a cap of ten yields no candidate but sampling metadata is still honest.
    assert near_duplicates(frame, "target", max_rows=10) == []
    frame.loc[0:1, "x"] = 5.0
    findings = near_duplicates(frame, "target", max_rows=10)
    assert findings[0].evidence["sampled"] is True
    assert findings[0].evidence["analyzed_rows"] == 10
    assert "sampled" in findings[0].description


def test_deterministic_repeat():
    frame = pd.DataFrame({"x": [1.001, 1.002, 1.003], "target": [0, 1, 0]})
    assert near_duplicates(frame, "target") == near_duplicates(frame, "target")


def test_nan_and_infinity_handled():
    frame = pd.DataFrame({"x": [np.nan, np.nan, np.inf, np.inf, 1.0], "target": [0, 1, 0, 1, 0]})
    findings = near_duplicates(frame, "target")
    assert findings and findings[0].affected_rows == 4


def test_unhashable_object_values_fail_clearly():
    frame = pd.DataFrame({"x": [["a"], ["b"]], "target": [0, 1]})
    with pytest.raises(ValueError, match="unhashable"):
        near_duplicates(frame, "target")


def test_wording_says_candidates_not_confirmed_duplicates():
    frame = pd.DataFrame({"x": [1.0, 1.0], "target": [0, 1]})
    finding = near_duplicates(frame, "target")[0]
    assert "candidate" in finding.title.lower()
    assert "rounded" in finding.description.lower()
