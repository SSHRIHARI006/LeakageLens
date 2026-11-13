"""Group overlap detector and group split tests (spec 5.4)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leakagelens.detectors import group_overlap
from leakagelens.evaluation import make_split


def test_no_group_column_returns_nothing():
    frame = pd.DataFrame({"x": [1, 2], "target": [0, 1]})
    assert group_overlap(frame, None, [0], [1]) == []


def test_missing_group_column_raises():
    frame = pd.DataFrame({"x": [1, 2], "target": [0, 1]})
    with pytest.raises(ValueError, match="not found"):
        group_overlap(frame, "entity", [0], [1])


def test_no_shared_groups():
    frame = pd.DataFrame({"entity": [1, 1, 2, 2], "target": [0, 1, 0, 1]})
    assert group_overlap(frame, "entity", [0, 1], [2, 3]) == []


def test_partial_overlap_reports_exact_shared_groups_and_rows():
    frame = pd.DataFrame({"entity": [1, 1, 2, 3, 2, 4], "target": [0, 1, 0, 1, 0, 1]})
    finding = group_overlap(frame, "entity", [0, 1, 2, 3], [4, 5])[0]
    assert finding.evidence["shared_groups"] == 1
    assert finding.evidence["affected_test_rows"] == 1
    assert finding.affected_rows == 1


def test_all_groups_shared_is_full_overlap():
    frame = pd.DataFrame({"entity": [1, 2, 1, 2], "target": [0, 1, 0, 1]})
    finding = group_overlap(frame, "entity", [0, 1], [2, 3])[0]
    assert finding.evidence["percent_test_rows"] == 100.0


def test_null_group_ids_excluded():
    frame = pd.DataFrame({"entity": [None, None, 1, 1], "target": [0, 1, 0, 1]})
    assert group_overlap(frame, "entity", [0, 1], [2, 3]) == []


def test_unhashable_group_values_raise():
    frame = pd.DataFrame({"entity": [["a"], ["b"]], "target": [0, 1]})
    with pytest.raises(ValueError, match="unhashable"):
        group_overlap(frame, "entity", [0], [1])


def test_group_split_has_zero_intersection_and_partitions_every_row(group_frame):
    train, test = make_split(group_frame, "target", "classification", seed=7, group="entity", strategy="group")
    groups = group_frame["entity"]
    assert set(groups.iloc[train]).isdisjoint(set(groups.iloc[test]))
    assert sorted(np.concatenate([train, test]).tolist()) == list(range(len(group_frame)))
    assert len(set(train.tolist()) & set(test.tolist())) == 0


def test_group_split_is_deterministic_for_seed(group_frame):
    first = make_split(group_frame, "target", "classification", seed=11, group="entity", strategy="group")
    second = make_split(group_frame, "target", "classification", seed=11, group="entity", strategy="group")
    assert np.array_equal(first[0], second[0]) and np.array_equal(first[1], second[1])


def test_group_split_requires_two_groups_and_supports_series():
    frame = pd.DataFrame({"x": range(6), "target": [0, 1] * 3})
    with pytest.raises(ValueError, match="group"):
        make_split(frame, "target", "classification", seed=1, strategy="group")
    frame = pd.DataFrame({"x": range(12), "target": [0, 1] * 6})
    groups = pd.Series([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
    with pytest.raises(ValueError, match="at least two distinct"):
        make_split(frame, "target", "classification", seed=1, groups=pd.Series([1] * len(frame)), strategy="group")
    train, test = make_split(frame, "target", "classification", seed=1, groups=groups, strategy="group")
    assert set(groups.iloc[train]).isdisjoint(set(groups.iloc[test]))
    with pytest.raises(ValueError, match="align positionally"):
        make_split(frame, "target", "classification", seed=1, groups=groups.iloc[:3], strategy="group")


def test_group_split_works_for_regression():
    frame = pd.DataFrame({"x": np.arange(20, dtype=float), "entity": np.repeat(np.arange(10), 2), "target": np.linspace(0, 1, 20)})
    train, test = make_split(frame, "target", "regression", seed=2, group="entity", strategy="group")
    assert set(frame["entity"].iloc[train]).isdisjoint(set(frame["entity"].iloc[test]))
