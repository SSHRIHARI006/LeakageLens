from __future__ import annotations

from .schemas import Finding


def aggregate(findings: list[Finding]) -> tuple[float, str, dict[str, float]]:
    """Aggregate findings into a bounded 0-100 priority score.

    The score takes the maximum signal per category (correlated findings from the
    same mechanism do not stack), sums across categories and scales by 0.55. It is
    a triage heuristic, not a calibrated probability of leakage.
    """
    signals: dict[str, float] = {}
    for finding in findings:
        score = min(100.0, max(0.0, float(finding.score)))
        signals[finding.category] = max(signals.get(finding.category, 0.0), score)
    score = round(min(100.0, max(0.0, sum(signals.values()) * 0.55)), 1)
    level = "LOW" if score < 20 else "MODERATE" if score < 40 else "HIGH" if score < 70 else "CRITICAL"
    return score, level, signals
