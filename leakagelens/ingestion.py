from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls", ".parquet"}
TASKS = {"classification", "regression"}
INFERENCE_CONTEXTS = {"iid", "temporal"}
SPLIT_STRATEGIES = {"random", "group", "chronological"}


def _csv_header(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return next(csv.reader(handle), [])
    except UnicodeDecodeError:
        # Non-UTF8 files are passed to pandas, which raises its own clear parser error.
        return []


def load_table(path: str | Path) -> pd.DataFrame:
    """Load a supported tabular file and validate its basic structure.

    Raises ``ValueError`` for unsupported extensions, unreadable/empty files and
    duplicate headers; ``FileNotFoundError`` when the path does not exist.
    """
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type '{path.suffix}'. Use CSV, XLSX, or Parquet.")
    if not path.exists():
        raise FileNotFoundError(str(path))
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            header = _csv_header(path)
            duplicates = sorted({name for name in header if header.count(name) > 1})
            if duplicates:
                raise ValueError(f"Dataset has duplicate column names: {duplicates}.")
            frame = pd.read_csv(path)
        elif suffix in {".xlsx", ".xls"}:
            frame = pd.read_excel(path)
        else:
            frame = pd.read_parquet(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("File contains no data rows or columns.") from exc
    except UnicodeDecodeError as exc:
        raise ValueError("File could not be decoded as text; save it as UTF-8.") from exc
    validate_frame(frame)
    return frame


def validate_frame(frame: pd.DataFrame, target: str | None = None, task: str = "classification") -> None:
    """Validate a dataframe before auditing or model fitting.

    Policy: empty frames, duplicate columns, missing targets, targets with missing
    values, single-class classification targets and non-numeric regression targets
    are rejected up front with a typed ``ValueError``. Missing target values are
    never silently dropped.
    """
    if task not in TASKS:
        raise ValueError(f"Unsupported task '{task}'. Use one of {sorted(TASKS)}.")
    if frame.empty:
        raise ValueError("Dataset is empty.")
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].tolist()
        raise ValueError(f"Dataset has duplicate column names: {duplicates}.")
    if target is not None:
        if target not in frame:
            raise ValueError(f"target column '{target}' was not found.")
        missing = int(frame[target].isna().sum())
        if missing:
            raise ValueError(
                f"Target column '{target}' has {missing} missing value(s). "
                "Remove or impute them explicitly before auditing (LeakageLens does not drop target rows)."
            )
        if task == "classification":
            classes = int(frame[target].nunique())
            if classes < 2:
                raise ValueError("Target must contain at least two non-null classes for classification.")
        else:
            if not pd.api.types.is_numeric_dtype(frame[target]):
                raise ValueError(f"Regression target '{target}' must be numeric.")
            if not np.isfinite(pd.to_numeric(frame[target], errors="coerce")).all():
                raise ValueError(f"Regression target '{target}' contains non-finite values.")


def profile(frame: pd.DataFrame, target: str | None = None) -> dict:
    """Return a JSON-safe dataset profile used by reports and the API."""
    categorical = frame.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    numerical = frame.select_dtypes(include="number").columns.tolist()
    possible_ids = [c for c in frame.columns if frame[c].nunique(dropna=False) >= max(2, len(frame) * .95)]
    distribution = frame[target].value_counts(dropna=False).to_dict() if target else {}
    return {
        "rows": int(len(frame)), "columns": int(len(frame.columns)), "dtypes": {c: str(t) for c, t in frame.dtypes.items()},
        "missing_values": {c: int(v) for c, v in frame.isna().sum().items()},
        "constant_columns": [c for c in frame if frame[c].nunique(dropna=False) <= 1],
        "all_null_columns": [c for c in frame if frame[c].isna().all()],
        "categorical_columns": categorical, "numerical_columns": numerical, "possible_id_columns": possible_ids,
        "target_distribution": distribution,
    }
