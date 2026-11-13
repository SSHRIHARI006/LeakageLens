"""Inflation formula and protocol-comparison tests (spec 5.9)."""
from __future__ import annotations

import numpy as np
import pytest

from leakagelens.evaluation import comparison_metadata, inflation
from leakagelens.schemas import EvaluationResult


def result(strategy: str, metrics: dict, fingerprint: str) -> EvaluationResult:
    return EvaluationResult(strategy, metrics, 75, 25, "", {"test_index_fingerprint": fingerprint, "split_strategy": strategy})


def test_higher_is_better_positive_delta():
    original = result("random", {"accuracy": 0.9}, "aaa")
    safer = result("group", {"accuracy": 0.8}, "bbb")
    delta = inflation(original, safer, "classification")["accuracy"]
    assert delta["absolute_inflation"] == pytest.approx(0.1)
    assert delta["direction"] == "higher_is_better"


def test_higher_is_better_negative_delta_preserved():
    original = result("random", {"accuracy": 0.8}, "aaa")
    safer = result("group", {"accuracy": 0.9}, "bbb")
    assert inflation(original, safer, "classification")["accuracy"]["absolute_inflation"] == pytest.approx(-0.1)


def test_equal_values_zero_delta():
    original = result("random", {"accuracy": 0.8}, "aaa")
    safer = result("random", {"accuracy": 0.8}, "aaa")
    assert inflation(original, safer, "classification")["accuracy"]["absolute_inflation"] == 0


def test_lower_is_better_rmse_direction():
    original = result("random", {"rmse": 10.0}, "aaa")
    safer = result("group", {"rmse": 12.0}, "bbb")
    delta = inflation(original, safer, "regression")["rmse"]
    assert delta["absolute_inflation"] == pytest.approx(2.0)
    assert delta["direction"] == "lower_is_better"


def test_lower_is_better_negative_delta():
    original = result("random", {"rmse": 12.0}, "aaa")
    safer = result("group", {"rmse": 10.0}, "bbb")
    assert inflation(original, safer, "regression")["rmse"]["absolute_inflation"] == pytest.approx(-2.0)


def test_zero_safer_value_has_undefined_relative_inflation():
    original = result("random", {"mae": 1.0}, "aaa")
    safer = result("group", {"mae": 0.0}, "bbb")
    assert inflation(original, safer, "regression")["mae"]["relative_inflation"] is None


def test_negative_r2_handled_consistently():
    original = result("random", {"r2": -0.5}, "aaa")
    safer = result("group", {"r2": -1.5}, "bbb")
    delta = inflation(original, safer, "regression")["r2"]
    assert delta["absolute_inflation"] == pytest.approx(1.0)
    assert delta["direction"] == "higher_is_better"


def test_missing_metric_in_safer_result_is_omitted():
    original = result("random", {"accuracy": 0.9, "f1": 0.8}, "aaa")
    safer = result("group", {"accuracy": 0.8}, "bbb")
    assert set(inflation(original, safer, "classification")) == {"accuracy"}


def test_non_finite_metrics_ignored():
    original = result("random", {"accuracy": np.nan}, "aaa")
    safer = result("group", {"accuracy": 0.8}, "bbb")
    assert inflation(original, safer, "classification") == {}


def test_comparison_metadata_detects_fixed_population():
    same = comparison_metadata(result("random", {}, "aaa"), result("group", {}, "aaa"))
    assert same["evaluation_rows_fixed"] is True
    assert "Same held-out rows" in same["interpretation"]
    changed = comparison_metadata(result("random", {}, "aaa"), result("group", {}, "bbb"))
    assert changed["evaluation_rows_fixed"] is False
    assert "not causal" in changed["interpretation"]
    assert changed["original_test_index_fingerprint"] == "aaa"
