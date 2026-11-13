"""Split construction and metric tests (spec 5.7/6.2)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin

from leakagelens.evaluation import _metrics_by_task, evaluate, make_split


def test_random_split_is_reproducible_and_disjoint(clean_frame):
    first = make_split(clean_frame, "target", "classification", 9)
    second = make_split(clean_frame, "target", "classification", 9)
    assert np.array_equal(first[0], second[0]) and np.array_equal(first[1], second[1])
    train, test = first
    assert not set(train.tolist()) & set(test.tolist())
    assert sorted(np.concatenate([train, test]).tolist()) == list(range(len(clean_frame)))


def test_stratified_split_preserves_class_ratio():
    frame = pd.DataFrame({"x": np.arange(200, dtype=float), "target": [0] * 150 + [1] * 50})
    train, test = make_split(frame, "target", "classification", 3)
    train_ratio = frame["target"].iloc[train].mean()
    assert abs(train_ratio - .25) < .03


@pytest.mark.parametrize("strategy", ["stratified", "unknown"])
def test_unknown_strategy_rejected(strategy):
    frame = pd.DataFrame({"x": [1, 2], "target": [0, 1]})
    with pytest.raises(ValueError, match="Unsupported split strategy"):
        make_split(frame, "target", "classification", 1, strategy=strategy)


def test_binary_numeric_positive_label_is_reported():
    metrics, note = _metrics_by_task(pd.Series([0, 1, 0, 1]), np.array([0, 1, 1, 0]), "classification")
    assert metrics["accuracy"] == 0.5
    assert "positive class is '1'" in note


def test_string_binary_labels_use_second_sorted_label_as_positive():
    metrics, note = _metrics_by_task(pd.Series(["no", "yes", "no", "yes"]), np.array(["no", "yes", "yes", "no"]), "classification")
    assert metrics["accuracy"] == 0.5
    assert "'yes'" in note
    assert all(np.isfinite(v) for v in metrics.values())


def test_non_standard_numeric_labels_supported():
    metrics, _ = _metrics_by_task(pd.Series([10, 20, 10, 20]), np.array([10, 20, 20, 10]), "classification")
    assert metrics["accuracy"] == 0.5


def test_multiclass_uses_weighted_metrics():
    y_true = pd.Series([0, 1, 2, 0, 1, 2])
    pred = np.array([0, 1, 2, 2, 1, 0])
    metrics, note = _metrics_by_task(y_true, pred, "classification")
    assert "Averaging=weighted" in note
    assert 0 <= metrics["f1"] <= 1


def test_single_label_present_in_test_does_not_crash():
    metrics, note = _metrics_by_task(pd.Series([0, 0, 0]), np.array([0, 0, 0]), "classification")
    assert metrics["accuracy"] == 1.0


def test_imbalanced_classes_have_finite_metrics():
    y_true = pd.Series([0] * 19 + [1])
    pred = np.array([0] * 19 + [1])
    metrics, _ = _metrics_by_task(y_true, pred, "classification")
    assert all(np.isfinite(v) for v in metrics.values())


def test_regression_metrics_match_hand_calculation():
    metrics, _ = _metrics_by_task(pd.Series([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 5.0]), "regression")
    assert metrics["mae"] == pytest.approx(2 / 3, abs=1e-5)
    assert metrics["rmse"] == pytest.approx(np.sqrt(4 / 3), abs=1e-5)
    assert metrics["r2"] == pytest.approx(-1.0, abs=1e-5)


def test_non_finite_and_undefined_metrics_are_omitted():
    metrics, note = _metrics_by_task(pd.Series([1.0, 1.0]), np.array([1.0, 1.0]), "regression")
    assert "r2" not in metrics
    assert "Undefined metrics omitted" in note


def test_evaluate_target_is_never_a_predictor(clean_frame):
    class TargetDetector(BaseEstimator, ClassifierMixin):
        def fit(self, X, y=None):
            assert "target" not in X.columns
            self.classes_ = np.unique(y)
            return self

        def predict(self, X):
            return np.full(len(X), self.classes_[0])

    train, test = np.arange(60), np.arange(60, 80)
    result = evaluate(clean_frame, "target", "classification", TargetDetector(), train, test, 1, "random")
    assert result.metrics["accuracy"] >= 0


def test_evaluation_result_protocol_records_population(clean_frame):
    result = evaluate(clean_frame, "target", "classification", None, np.arange(60), np.arange(60, 80), 1, "random", group="segment")
    assert result.protocol["split_strategy"] == "random"
    assert result.protocol["train_size"] == 60
    assert result.protocol["test_size"] == 20
    assert result.protocol["group_column"] == "segment"
    assert len(result.protocol["test_index_fingerprint"]) == 16


def test_regression_default_pipeline_runs(clean_frame):
    frame = clean_frame.copy()
    frame["target"] = frame["age"] * .1 + frame["spend"] * .01
    result = evaluate(frame, "target", "regression", None, np.arange(60), np.arange(60, 80), 2, "random")
    assert "rmse" in result.metrics
