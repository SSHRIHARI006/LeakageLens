"""Shared deterministic fixtures for the LeakageLens test suite.

Fixtures build small dataframes in memory; no fixture writes ground-truth
metadata into the frame that a detector sees.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def clean_frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 80
    age = rng.normal(45, 10, n).round(1)
    spend = rng.normal(100, 20, n).round(1)
    target = (age * .05 + spend * .01 + rng.normal(0, 1, n) > 3.25).astype(int)
    return pd.DataFrame({"age": age, "spend": spend, "segment": rng.choice(["A", "B"], n), "target": target})


@pytest.fixture
def duplicate_frame() -> pd.DataFrame:
    """Eight rows, the first two identical, target excluded from hashing."""
    return pd.DataFrame({
        "age": [30, 30, 40, 50, 60, 70, 80, 90],
        "spend": [10, 10, 20, 30, 40, 50, 60, 70],
        "target": [0, 0, 1, 0, 1, 1, 0, 1],
    })


@pytest.fixture
def group_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "x": np.arange(20, dtype=float),
        "entity": np.repeat(np.arange(10), 2),
        "target": np.arange(20) % 2,
    })


@pytest.fixture
def temporal_frame() -> pd.DataFrame:
    n = 40
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "x": np.arange(n, dtype=float),
        "event_date": dates,
        "target": np.arange(n) % 2,
    })


def make_frame(rows: int = 12, target: str = "target") -> pd.DataFrame:
    """Minimal numeric frame whose feature values follow the row position."""
    return pd.DataFrame({"x": np.arange(rows, dtype=float), target: np.arange(rows) % 2})


@pytest.fixture
def frame_factory():
    return make_frame


class SpyTransformer:
    """Records the exact row index labels passed to ``fit`` and ``transform``."""

    def __init__(self):
        self.fit_index: list = []
        self.transform_index: list = []

    def fit(self, X, y=None):
        self.fit_index = list(getattr(X, "index", []))
        return self

    def transform(self, X):
        self.transform_index = list(getattr(X, "index", []))
        return X

    def fit_transform(self, X, y=None):
        self.fit(X, y)
        return self.transform(X)

    def get_params(self, deep=True):
        return {}

    def set_params(self, **params):
        return self
