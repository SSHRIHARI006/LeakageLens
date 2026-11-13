from __future__ import annotations

import hashlib
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .schemas import EvaluationResult

Splittable = Literal["random", "group", "chronological"]


def _dates_to_epoch(values):
    frame = pd.DataFrame(values).copy()
    for column in frame:
        series = pd.to_datetime(frame[column], errors="coerce")
        frame[column] = series.astype("int64").where(series.notna(), np.nan) / 1_000_000_000
    return frame


def default_pipeline(frame: pd.DataFrame, target: str, task: str, seed: int):
    """Build the default preprocessing + model pipeline.

    Learned preprocessing lives inside the pipeline so that LeakageLens can fit it
    on the training partition only. Entirely-null columns are removed up front
    because they carry no signal and would otherwise make the imputer drop the
    whole feature block.
    """
    X = frame.drop(columns=[target]).loc[:, lambda d: ~d.isna().all()]
    nums = X.select_dtypes(include=np.number).columns.tolist()
    dates = X.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    cats = [c for c in X.columns if c not in nums + dates]
    if not X.columns.size:
        raise ValueError("No usable feature columns remain after removing the target and all-null columns.")
    transformers = []
    if nums:
        transformers.append(("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), nums))
    if dates:
        transformers.append(("date", Pipeline([("epoch", FunctionTransformer(_dates_to_epoch, validate=False)), ("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), dates))
    if cats:
        transformers.append(("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), cats))
    pre = ColumnTransformer(transformers, remainder="drop")
    model = RandomForestClassifier(n_estimators=150, random_state=seed) if task == "classification" else RandomForestRegressor(n_estimators=150, random_state=seed)
    return Pipeline([("preprocessor", pre), ("model", model)])


def make_split(frame: pd.DataFrame, target: str, task: str, seed: int, group: str | None = None, time: str | None = None, strategy: str = "random", groups: pd.Series | None = None):
    """Return positional train/test indices for the requested split strategy."""
    if strategy not in {"random", "group", "chronological"}:
        raise ValueError(f"Unsupported split strategy '{strategy}'. Use random, group, or chronological.")
    idx = np.arange(len(frame))
    y = frame[target]
    if strategy == "group":
        if group is None and groups is None:
            raise ValueError("A group strategy requires a group column or group series.")
        split_groups = groups if groups is not None else frame[group]
        if len(split_groups) != len(frame):
            raise ValueError("Group series must align positionally with the dataframe rows.")
        valid = split_groups.dropna()
        if valid.nunique() < 2:
            raise ValueError("Group split requires at least two distinct non-null groups.")
        train, test = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=seed).split(idx, y, groups=split_groups))
    elif strategy == "chronological":
        if not time:
            raise ValueError("A chronological strategy requires a time column.")
        if time not in frame:
            raise ValueError(f"Time column '{time}' was not found.")
        dates = pd.to_datetime(frame[time], errors="coerce")
        if dates.isna().all():
            raise ValueError(f"Time column '{time}' cannot be parsed.")
        if dates.isna().any():
            raise ValueError(f"Time column '{time}' has {int(dates.isna().sum())} unparseable value(s); a chronological split is unreliable.")
        ordered = np.argsort(dates.to_numpy(), kind="stable")
        cut = max(1, int(.75 * len(ordered)))
        if cut >= len(ordered):
            raise ValueError("Dataset is too small for a chronological split with a non-empty test partition.")
        train, test = ordered[:cut], ordered[cut:]
    else:
        stratify = y if task == "classification" and y.value_counts().min() >= 2 else None
        train, test = train_test_split(idx, test_size=.25, random_state=seed, stratify=stratify)
    train, test = np.asarray(train, dtype=int), np.asarray(test, dtype=int)
    if not len(train) or not len(test):
        raise ValueError("Split produced an empty train or test partition.")
    return train, test


def _fingerprint(indices: np.ndarray) -> str:
    return hashlib.sha256(",".join(str(int(i)) for i in sorted(indices)).encode("utf-8")).hexdigest()[:16]


def _metrics_by_task(y_true: pd.Series, pred: np.ndarray, task: str) -> tuple[dict[str, float], str]:
    note = ""
    if task == "classification":
        labels = sorted(set(y_true.tolist()) | set(np.asarray(pred).tolist()), key=lambda v: (str(type(v)), str(v)))
        if len(labels) == 2:
            avg, extra = "binary", {"pos_label": labels[1]}
        else:
            avg, extra = "weighted", {}
        metrics = {
            "accuracy": accuracy_score(y_true, pred),
            "precision": precision_score(y_true, pred, average=avg, zero_division=0, **extra),
            "recall": recall_score(y_true, pred, average=avg, zero_division=0, **extra),
            "f1": f1_score(y_true, pred, average=avg, zero_division=0, **extra),
        }
        note = f"Binary positive class is '{labels[1]}'; averaging={avg}." if len(labels) == 2 else f"Averaging={avg} across {len(labels)} classes."
    else:
        metrics = {
            "mae": mean_absolute_error(y_true, pred),
            "rmse": mean_squared_error(y_true, pred) ** .5,
            "r2": r2_score(y_true, pred),
        }
        if y_true.nunique(dropna=False) <= 1:
            metrics.pop("r2")
            note = "Undefined metrics omitted: r2 is undefined when the held-out target is constant."
    finite = {k: round(float(v), 5) for k, v in metrics.items() if np.isfinite(v)}
    undefined = sorted(set(metrics) - set(finite))
    if undefined:
        note = (note + " " if note else "") + f"Undefined metrics omitted: {', '.join(undefined)}."
    return finite, note


def evaluate(frame: pd.DataFrame, target: str, task: str, pipeline: object | None, train: np.ndarray, test: np.ndarray, seed: int, strategy: str, group: str | None = None, time: str | None = None) -> EvaluationResult:
    """Fit on the training partition only and score the test partition."""
    X = frame.drop(columns=[target]); y = frame[target]
    estimator = clone(pipeline) if pipeline is not None else default_pipeline(frame, target, task, seed)
    estimator.fit(X.iloc[train], y.iloc[train]); pred = estimator.predict(X.iloc[test])
    metrics, note = _metrics_by_task(y.iloc[test], pred, task)
    protocol = {
        "split_strategy": strategy, "test_population": "held_out_test_partition", "seed": seed,
        "train_size": int(len(train)), "test_size": int(len(test)),
        "train_index_fingerprint": _fingerprint(train), "test_index_fingerprint": _fingerprint(test),
        "group_column": group, "time_column": time,
        "estimator": type(estimator).__name__,
    }
    return EvaluationResult(strategy, metrics, int(len(train)), int(len(test)), note, protocol)


def inflation(original: EvaluationResult, safer: EvaluationResult, task: str) -> dict:
    """Direction-aware observed metric differences between the two protocols.

    A positive value means the original protocol looks better than the safer one
    (i.e. the observed score difference is consistent with inflation), a negative
    value means it looks worse. This is not a causal estimate unless the evaluation
    rows are held fixed.
    """
    out = {}
    for metric, old in original.metrics.items():
        new = safer.metrics.get(metric)
        if new is None:
            continue
        if not (np.isfinite(old) and np.isfinite(new)):
            continue
        higher = metric not in {"mae", "rmse"}
        delta = old - new if higher else new - old
        out[metric] = {
            "original": old, "safer": new, "absolute_inflation": round(delta, 5),
            "relative_inflation": round(delta / abs(new), 5) if new else None,
            "direction": "higher_is_better" if higher else "lower_is_better",
        }
    return out


def comparison_metadata(original: EvaluationResult, safer: EvaluationResult) -> dict:
    """Describe whether the two evaluations scored the same population."""
    old_fp = original.protocol.get("test_index_fingerprint")
    new_fp = safer.protocol.get("test_index_fingerprint")
    fixed = bool(old_fp and new_fp and old_fp == new_fp)
    return {
        "evaluation_rows_fixed": fixed,
        "original_split_strategy": original.strategy,
        "safer_split_strategy": safer.strategy,
        "original_test_size": original.test_size,
        "safer_test_size": safer.test_size,
        "original_test_index_fingerprint": old_fp,
        "safer_test_index_fingerprint": new_fp,
        "interpretation": (
            "Same held-out rows; differences isolate the leakage condition where the estimator is unchanged."
            if fixed else
            "Different split strategies and evaluation populations; report values as observed protocol differences, not causal leakage inflation."
        ),
    }
