from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping

import numpy as np
import pandas as pd

Severity = Literal["low", "moderate", "high", "critical"]


def jsonable(value: Any) -> Any:
    """Recursively convert numpy/pandas scalars and containers into JSON-safe values.

    Non-finite floats (NaN/inf) are represented as ``None`` so that a payload can
    always be serialized with ``json.dumps``. Timestamps become ISO strings.
    """
    if value is None:
        return None
    if isinstance(value, (str, bool, int)) and not isinstance(value, np.generic):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.datetime64,)):
        return str(value)
    if isinstance(value, Mapping):
        return {str(jsonable(k)): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return [jsonable(v) for v in value.tolist()]
    if isinstance(value, pd.Series):
        return jsonable(value.to_dict())
    if isinstance(value, pd.DataFrame):
        return jsonable(value.to_dict(orient="list"))
    return str(value)


@dataclass
class Finding:
    detector_name: str
    category: str
    severity: Severity
    confidence: str
    score: float
    title: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    affected_columns: list[str] = field(default_factory=list)
    affected_rows: int | None = None
    recommendation: str = "Review the finding in the context of the intended inference scenario."
    verification_status: str = "heuristic"

    def __post_init__(self) -> None:
        # Findings are bounded signals; never allow an out-of-range score to distort aggregation.
        self.score = float(min(100.0, max(0.0, float(self.score))))

    def to_dict(self) -> dict[str, Any]:
        return jsonable(asdict(self))


@dataclass
class EvaluationResult:
    strategy: str
    metrics: dict[str, float]
    train_size: int
    test_size: int
    note: str = ""
    protocol: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return jsonable(asdict(self))


@dataclass
class AuditResult:
    dataset_summary: dict[str, Any]
    findings: list[Finding]
    risk_score: float
    risk_level: str
    signal_scores: dict[str, float]
    original_evaluation: EvaluationResult | None = None
    safer_evaluation: EvaluationResult | None = None
    inflation: dict[str, Any] | None = None
    reproducibility: dict[str, Any] = field(default_factory=dict)
    comparison: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        return jsonable(value)
