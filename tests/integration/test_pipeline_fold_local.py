"""Learned preprocessing must be fitted on the training partition only (spec 6.3)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

from leakagelens.evaluation import evaluate


class RecordingEstimator(BaseEstimator, ClassifierMixin):
    fits: list[list] = []
    predicts: list[list] = []

    def fit(self, X, y=None):
        RecordingEstimator.fits.append(list(X.index))
        self.classes_ = np.unique(y)
        return self

    def predict(self, X):
        RecordingEstimator.predicts.append(list(X.index))
        return np.repeat(self.classes_[0], len(X))


def test_fit_sees_only_training_rows_and_predict_only_test_rows():
    RecordingEstimator.fits, RecordingEstimator.predicts = [], []
    frame = pd.DataFrame({"x": np.arange(20, dtype=float), "target": [0, 1] * 10}, index=np.arange(100, 120))
    train, test = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]), np.array([14, 15, 16, 17, 18, 19])
    evaluate(frame, "target", "classification", RecordingEstimator(), train, test, 1, "random")
    assert RecordingEstimator.fits == [frame.index[train].tolist()]
    assert RecordingEstimator.predicts == [frame.index[test].tolist()]
    assert set(RecordingEstimator.fits[0]).isdisjoint(RecordingEstimator.predicts[0])


def test_extreme_test_values_are_absent_from_the_fit_data():
    frame = pd.DataFrame({
        "x": [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1_000_000.0, 1_000_000.0],
        "cat": ["a", "b", "a", "b", "a", "b", "a", "b", "z", "z"],
        "target": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    })
    train = np.arange(0, 8)
    test = np.arange(8, 10)
    seen_max: list[float] = []

    class MaxRecorder(BaseEstimator, ClassifierMixin):
        def fit(self, X, y=None):
            seen_max.append(float(X["x"].max()))
            self.classes_ = np.unique(y)
            return self

        def predict(self, X):
            return np.repeat(self.classes_[0], len(X))

    evaluate(frame, "target", "classification", MaxRecorder(), train, test, 1, "random")
    assert seen_max == [1.0]


def test_no_leaky_target_derived_feature_is_created_by_audit():
    from leakagelens import AuditConfig, LeakageLens

    frame = pd.DataFrame({"x": np.arange(30, dtype=float), "target": np.arange(30) % 2})
    result = LeakageLens(AuditConfig(target="target", seed=1)).audit(frame)
    assert result.original_evaluation.protocol["estimator"] == "Pipeline"
    assert result.reproducibility["pipeline"] == "default_pipeline"
