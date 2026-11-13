"""Pipeline audit and default pipeline tests (spec 5.7)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from leakagelens.detectors import pipeline_audit
from leakagelens.evaluation import default_pipeline, evaluate


def test_no_pipeline_reports_unable_to_determine():
    finding = pipeline_audit(None)[0]
    assert finding.verification_status == "unable_to_determine"
    assert finding.severity == "low"


def test_compatible_estimator_is_verified():
    finding = pipeline_audit(LogisticRegression())[0]
    assert finding.verification_status == "verified"


def test_object_missing_fit_or_predict_is_unsupported():
    class FitOnly:
        def fit(self, X, y=None):
            return self

    class PredictOnly:
        def predict(self, X):
            return np.zeros(len(X))

    for obj in (FitOnly(), PredictOnly()):
        finding = pipeline_audit(obj)[0]
        assert finding.verification_status == "unable_to_determine"
        assert "Unsupported" in finding.title


def test_default_pipeline_handles_mixed_types_and_all_null_columns():
    frame = pd.DataFrame({
        "num": [1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0],
        "cat": ["a", "b", "a", "b", "a", "b", "a", "b"],
        "when": pd.date_range("2024-01-01", periods=8),
        "all_null": [np.nan] * 8,
        "target": [0, 1, 0, 1, 0, 1, 0, 1],
    })
    pipeline = default_pipeline(frame, "target", "classification", 3)
    train, test = np.arange(0, 6), np.arange(6, 8)
    result = evaluate(frame, "target", "classification", pipeline, train, test, 3, "random")
    assert 0 <= result.metrics["accuracy"] <= 1


def test_default_pipeline_requires_usable_features():
    frame = pd.DataFrame({"target": [0, 1]})
    with pytest.raises(ValueError, match="No usable feature columns"):
        default_pipeline(frame, "target", "classification", 1)


def test_custom_pipeline_with_unseen_category_and_string_labels():
    frame = pd.DataFrame({
        "cat": ["a", "a", "a", "a", "b", "b", "c", "c"],
        "num": [0, 1, 2, 3, 4, 5, 6, 7],
        "target": ["no", "no", "no", "no", "yes", "yes", "yes", "yes"],
    })
    pipeline = Pipeline([
        ("prep", ColumnTransformer([
            ("num", StandardScaler(), ["num"]),
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["cat"]),
        ])),
        ("model", LogisticRegression(max_iter=200)),
    ])
    result = evaluate(frame, "target", "classification", pipeline, np.arange(0, 6), np.arange(6, 8), 1, "random")
    assert "accuracy" in result.metrics


def test_unsupported_pipeline_error_is_actionable():
    frame = pd.DataFrame({"x": range(10), "target": [0, 1] * 5})

    from sklearn.base import BaseEstimator, ClassifierMixin

    class Broken(BaseEstimator, ClassifierMixin):
        def fit(self, X, y=None):
            raise RuntimeError("boom")

        def predict(self, X):
            return np.zeros(len(X))

    with pytest.raises(RuntimeError, match="boom"):
        evaluate(frame, "target", "classification", Broken(), np.arange(8), np.arange(8, 10), 1, "random")
