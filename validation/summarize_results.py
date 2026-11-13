"""Summarize a benchmark run into a Markdown validation report.

Usage:
    python -m validation.summarize_results --input validation/results --output docs/validation_results.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _latest_run(input_dir: Path) -> Path:
    runs = sorted(p for p in input_dir.iterdir() if p.is_dir() and (p / "summary.json").exists())
    if not runs:
        raise SystemExit(f"No benchmark runs with summary.json found in {input_dir}")
    return max(runs, key=lambda p: (p / "summary.json").stat().st_mtime)


def render(summary: dict, run_dir: Path) -> str:
    lines = [
        "# LeakageLens synthetic benchmark results", "",
        f"Generated from `{run_dir}`. Every number below was produced by running the benchmark code; no result is hand-entered.",
        "", "## Run metadata", "",
        f"- run id: `{summary['run_id']}`", f"- created (UTC): {summary['created_utc']}",
        f"- Python: {summary['python']}", f"- platform: {summary['platform']}",
        f"- families: {', '.join(summary['families'])}", f"- seeds per family: {summary['seed_count']} ({summary['seeds'][0]}–{summary['seeds'][-1]})",
        "", "## Per-detector confusion matrix and metrics", "",
        "| Detector | TP | FP | FN | TN | Precision | Recall | Specificity | FPR | FNR | F1 | Count accuracy | Mean runtime (ms) | Errors |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for detector, s in summary["detectors"].items():
        lines.append(
            f"| `{detector}` | {s['tp']} | {s['fp']} | {s['fn']} | {s['tn']} | {_fmt(s['precision'])} | {_fmt(s['recall'])} | "
            f"{_fmt(s['specificity'])} | {_fmt(s['false_positive_rate'])} | {_fmt(s['false_negative_rate'])} | {_fmt(s['f1'])} | "
            f"{_fmt(s['count_accuracy'])} ({s['count_cases']}) | {_fmt(s['mean_runtime_ms'], 1)} | {s['errors']} |"
        )
    lines += ["", "`undefined` means the denominator was zero, not a perfect score. Precision/recall over heuristic feature warnings are warning precision/recall, not leakage proof.", "", "## Multiple-seed stability", "",
              "| Detector | Seeds | Overall accuracy | Mean ± std | Median [IQR] | 95% CI (normal approx.) |",
              "|---|---|---|---|---|---|"]
    for detector, m in summary["multiseed"].items():
        ci = f"[{m['ci95'][0]}, {m['ci95'][1]}]" if m["ci95"] else "undefined"
        lines.append(f"| `{detector}` | {m['seed_count']} | {_fmt(m['overall_accuracy'])} | {_fmt(m['mean'])} ± {_fmt(m['std'])} | {_fmt(m['median'])} [{_fmt(m['q1'])}, {_fmt(m['q3'])}] | {ci} |")
    lines += ["", "## Per-family outcomes", "", "| Family | Expected | Detected | Detector | Seed |", "|---|---|---|---|---|"]
    for record in summary["records"]:
        if record["expected"] or record["detected"]:
            lines.append(f"| {record['family']} | {record['expected']} | {record['detected']} | `{record['detector']}` | {record['seed']} |")
    lines += ["", "## Original versus safer evaluation (observed protocol differences)", ""]
    inflation = summary.get("inflation") or []
    if not inflation:
        lines.append("No inflation experiments were run in this benchmark run.")
    for entry in inflation:
        if entry.get("error"):
            lines.append(f"- {entry['family']} seed {entry['seed']}: error `{entry['error']}`")
            continue
        fixed = (entry.get("comparison") or {}).get("evaluation_rows_fixed")
        deltas = ", ".join(f"{name} {values['absolute_inflation']:+.4f}" for name, values in (entry.get("inflation") or {}).items())
        lines.append(f"- {entry['family']} seed {entry['seed']}: original `{entry['original_strategy']}` vs safer `{entry['safer_strategy']}`; rows fixed = `{fixed}`; deltas: {deltas or 'none'}")
    lines += ["", "## Caveats", ""] + [f"- {caveat}" for caveat in summary.get("caveats", [])] + [""]
    for skipped in summary.get("skipped", []):
        lines.append(f"- Skipped: {skipped['family']} — {skipped['reason']}")
    lines += ["", "See [validation_methodology.md](validation_methodology.md) for the protocol and [known_limitations.md](known_limitations.md) for scope.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize LeakageLens benchmark results.")
    parser.add_argument("--input", default="validation/results")
    parser.add_argument("--output", default="docs/validation_results.md")
    parser.add_argument("--run", default=None, help="Specific run directory (defaults to the latest).")
    args = parser.parse_args(argv)
    run_dir = Path(args.run) if args.run else _latest_run(Path(args.input))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(summary, run_dir), encoding="utf-8")
    print(f"Wrote {output} from {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
