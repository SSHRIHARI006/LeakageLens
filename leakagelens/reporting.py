from __future__ import annotations
from pathlib import Path
from .schemas import AuditResult

def markdown_report(result: AuditResult) -> str:
    lines = ["# LeakageLens audit report", "", "## Executive summary", "", f"Leakage risk score: **{result.risk_score}/100 ({result.risk_level})**. This is an interpretable priority score, not a probability or proof of leakage.", "", "## Dataset", ""]
    lines += [f"- {k}: {v}" for k, v in result.dataset_summary.items() if k in {"rows", "columns", "possible_id_columns", "constant_columns"}]
    lines += ["", "## Findings", ""]
    for f in result.findings:
        lines += [f"### {f.title}", f"- Detector: {f.detector_name}", f"- Severity / confidence: {f.severity} / {f.confidence}", f"- Verification: {f.verification_status}", f"- Evidence: {f.evidence}", f"- Recommendation: {f.recommendation}", ""]
    if result.inflation:
        lines += ["## Original versus safer evaluation", "", "Performance differences are protocol-specific and are not asserted as a true-score correction.", ""]
        for metric, values in result.inflation.items(): lines.append(f"- {metric}: original {values['original']}, safer {values['safer']}, observed inflation {values['absolute_inflation']}.")
    lines += ["", "## Reproducibility", "", f"{result.reproducibility}", "", "## Limitations", "", "Feature legitimacy and deployment semantics require domain validation. Near-duplicate and feature warnings are heuristic; unsupported pipelines cannot be fully inspected."]
    return "\n".join(lines)

def write_report(result: AuditResult, path: str | Path) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(markdown_report(result), encoding="utf-8"); return path
