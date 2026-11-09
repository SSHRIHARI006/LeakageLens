from __future__ import annotations
from .schemas import Finding

def aggregate(findings: list[Finding]) -> tuple[float, str, dict[str, float]]:
    signals: dict[str, float] = {}
    for finding in findings:
        signals[finding.category] = max(signals.get(finding.category, 0), finding.score)
    score = round(min(100, sum(signals.values()) * 0.55), 1)
    level = "LOW" if score < 20 else "MODERATE" if score < 40 else "HIGH" if score < 70 else "CRITICAL"
    return score, level, signals
