from __future__ import annotations
from typing import Literal
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from .schemas import EvaluationResult

def _dates_to_epoch(values):
    frame = pd.DataFrame(values).copy()
    for column in frame:
        series = pd.to_datetime(frame[column], errors="coerce")
        frame[column] = series.astype("int64").where(series.notna(), np.nan) / 1_000_000_000
    return frame

def default_pipeline(frame: pd.DataFrame, target: str, task: str, seed: int):
    X = frame.drop(columns=[target]); nums = X.select_dtypes(include=np.number).columns.tolist(); dates = X.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist(); cats = [c for c in X.columns if c not in nums + dates]
    pre = ColumnTransformer([("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), nums), ("date", Pipeline([("epoch", FunctionTransformer(_dates_to_epoch, validate=False)), ("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), dates), ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), cats)], remainder="drop")
    model = RandomForestClassifier(n_estimators=150, random_state=seed) if task == "classification" else RandomForestRegressor(n_estimators=150, random_state=seed)
    return Pipeline([("preprocessor", pre), ("model", model)])

def make_split(frame: pd.DataFrame, target: str, task: str, seed: int, group: str | None = None, time: str | None = None, strategy: str = "random", groups: pd.Series | None = None):
    idx = np.arange(len(frame)); y = frame[target]
    if strategy == "group" and (group or groups is not None):
        split_groups = groups if groups is not None else frame[group]
        train, test = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=seed).split(idx, y, groups=split_groups))
    elif strategy == "chronological" and time:
        dates = pd.to_datetime(frame[time], errors="coerce")
        if dates.isna().all(): raise ValueError(f"Time column '{time}' cannot be parsed.")
        ordered = np.argsort(dates.fillna(dates.min()).to_numpy()); cut = max(1, int(.75 * len(ordered))); train, test = ordered[:cut], ordered[cut:]
    else:
        stratify = y if task == "classification" and y.value_counts().min() >= 2 else None
        train, test = train_test_split(idx, test_size=.25, random_state=seed, stratify=stratify)
    return np.asarray(train), np.asarray(test)

def evaluate(frame: pd.DataFrame, target: str, task: str, pipeline: object | None, train: np.ndarray, test: np.ndarray, seed: int, strategy: str) -> EvaluationResult:
    X = frame.drop(columns=[target]); y = frame[target]
    estimator = clone(pipeline) if pipeline is not None else default_pipeline(frame, target, task, seed)
    estimator.fit(X.iloc[train], y.iloc[train]); pred = estimator.predict(X.iloc[test])
    if task == "classification":
        avg = "binary" if y.nunique() == 2 else "weighted"
        metrics = {"accuracy": accuracy_score(y.iloc[test], pred), "precision": precision_score(y.iloc[test], pred, average=avg, zero_division=0), "recall": recall_score(y.iloc[test], pred, average=avg, zero_division=0), "f1": f1_score(y.iloc[test], pred, average=avg, zero_division=0)}
    else:
        metrics = {"mae": mean_absolute_error(y.iloc[test], pred), "rmse": mean_squared_error(y.iloc[test], pred) ** .5, "r2": r2_score(y.iloc[test], pred)}
    return EvaluationResult(strategy, {k: round(float(v), 5) for k, v in metrics.items()}, len(train), len(test))

def inflation(original: EvaluationResult, safer: EvaluationResult, task: str) -> dict:
    out = {}
    for metric, old in original.metrics.items():
        new = safer.metrics.get(metric)
        if new is None: continue
        higher = metric not in {"mae", "rmse"}
        delta = old - new if higher else new - old
        out[metric] = {"original": old, "safer": new, "absolute_inflation": round(delta, 5), "relative_inflation": round(delta / abs(new), 5) if new else None, "direction": "higher_is_better" if higher else "lower_is_better"}
    return out
