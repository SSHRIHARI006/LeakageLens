from __future__ import annotations

import json
from pathlib import Path

from .schemas import AuditResult


def markdown_report(result: AuditResult) -> str:
    summary = result.dataset_summary
    lines = [
        "# LeakageLens audit report", "", "## Executive summary", "",
        f"Leakage risk score: **{result.risk_score}/100 ({result.risk_level})**. This is an interpretable priority score, not a probability or proof of leakage.",
        "", "## Dataset", "",
        f"- rows: {summary.get('rows')}", f"- columns: {summary.get('columns')}",
        f"- possible_id_columns: {summary.get('possible_id_columns')}", f"- constant_columns: {summary.get('constant_columns')}",
        f"- all_null_columns: {summary.get('all_null_columns')}", f"- target_distribution: {summary.get('target_distribution')}",
        "", f"Findings: {len(result.findings)}.",
        "", "## Findings", "",
    ]
    if not result.findings:
        lines += ["No deterministic or heuristic leakage findings were reported.", ""]
    for f in result.findings:
        lines += [
            f"### {f.title}", f"- Detector: {f.detector_name} (category: {f.category})",
            f"- Severity / confidence: {f.severity} / {f.confidence}",
            f"- Score: {f.score}", f"- Verification: {f.verification_status}",
            f"- Description: {f.description}", f"- Affected columns: {f.affected_columns}",
            f"- Affected rows: {f.affected_rows}", f"- Evidence: {json.dumps(f.to_dict()['evidence'], sort_keys=True)}",
            f"- Recommendation: {f.recommendation}", "",
        ]
    if result.original_evaluation and result.safer_evaluation:
        lines += ["## Original versus safer evaluation", ""]
        if result.comparison:
            lines += [f"- Evaluation rows fixed: {result.comparison.get('evaluation_rows_fixed')}",
                      f"- Original protocol: {result.comparison.get('original_split_strategy')} ({result.comparison.get('original_test_size')} test rows)",
                      f"- Safer protocol: {result.comparison.get('safer_split_strategy')} ({result.comparison.get('safer_test_size')} test rows)",
                      f"- Interpretation: {result.comparison.get('interpretation')}", ""]
        else:
            lines += ["Performance differences are protocol-specific and are not asserted as a true-score correction.", ""]
        for name, evaluation in (("Original", result.original_evaluation), ("Safer", result.safer_evaluation)):
            lines.append(f"- {name} ({evaluation.strategy}, train={evaluation.train_size}, test={evaluation.test_size}): {evaluation.metrics}")
            if evaluation.note:
                lines.append(f"  - Note: {evaluation.note}")
        lines.append("")
        if result.inflation:
            lines += ["Metric differences (a positive value means the original protocol looks better):", ""]
            for metric, values in result.inflation.items():
                relative = values["relative_inflation"]
                relative_text = "undefined (safer value is zero)" if relative is None else relative
                lines.append(f"- {metric}: original {values['original']}, safer {values['safer']}, absolute {values['absolute_inflation']}, relative {relative_text} ({values['direction']}).")
    lines += [
        "", "## Reproducibility", "",
        f"```json\n{json.dumps(result.reproducibility, indent=2, sort_keys=True, default=str)}\n```",
        "", "## Limitations", "",
        "- Feature legitimacy and deployment semantics require domain validation.",
        "- Near-duplicate and feature warnings are heuristic; they are candidates, not confirmed leakage.",
        "- Pipeline support is a compatibility check plus fold-local fitting, not a static audit of preprocessing performed before upload.",
        "- The risk score is a triage heuristic, not a calibrated probability of leakage.",
    ]
    return "\n".join(lines) + "\n"


def write_report(result: AuditResult, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_report(result), encoding="utf-8")
    return path
