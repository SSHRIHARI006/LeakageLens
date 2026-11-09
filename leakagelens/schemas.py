from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["low", "moderate", "high", "critical"]

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class EvaluationResult:
    strategy: str
    metrics: dict[str, float]
    train_size: int
    test_size: int
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

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

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        return value
