from __future__ import annotations
from pathlib import Path
import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls", ".parquet"}

def load_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type '{path.suffix}'. Use CSV, XLSX, or Parquet.")
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        frame = pd.read_excel(path)
    else:
        frame = pd.read_parquet(path)
    validate_frame(frame)
    return frame

def validate_frame(frame: pd.DataFrame, target: str | None = None) -> None:
    if frame.empty:
        raise ValueError("Dataset is empty.")
    if frame.columns.duplicated().any():
        raise ValueError("Dataset has duplicate column names.")
    if target is not None:
        if target not in frame:
            raise ValueError(f"Target column '{target}' was not found.")
        if frame[target].dropna().nunique() < 2:
            raise ValueError("Target must contain at least two non-null values.")

def profile(frame: pd.DataFrame, target: str | None = None) -> dict:
    categorical = frame.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    numerical = frame.select_dtypes(include="number").columns.tolist()
    possible_ids = [c for c in frame.columns if frame[c].nunique(dropna=False) >= max(2, len(frame) * .95)]
    return {
        "rows": len(frame), "columns": len(frame.columns), "dtypes": {c: str(t) for c, t in frame.dtypes.items()},
        "missing_values": frame.isna().sum().to_dict(), "constant_columns": [c for c in frame if frame[c].nunique(dropna=False) <= 1],
        "categorical_columns": categorical, "numerical_columns": numerical, "possible_id_columns": possible_ids,
        "target_distribution": frame[target].value_counts(dropna=False).to_dict() if target else {},
    }
