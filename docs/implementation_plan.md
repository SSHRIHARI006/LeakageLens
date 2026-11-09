# LeakageLens implementation plan

## Goal

Deliver a reproducible Python application that audits a tabular dataset and a supported scikit-learn pipeline, reports multi-signal evidence, performs a safer alternative evaluation when configured, and quantifies the observed performance difference.

## Scope of the first complete release

1. **Foundation:** package layout, typed schemas, CSV/XLSX/Parquet ingestion, validation, dataset profile, seed/config capture, and tests.
2. **Deterministic data/split audit:** exact duplicates, supplied group overlap, supplied temporal ordering, split distribution, and ID/date candidates.
3. **Heuristic evidence:** scalable near-duplicate candidate checks, suspicious names/high association, single-feature baseline, optional target permutation.
4. **Pipeline audit:** inspect supported sklearn `Pipeline`/`ColumnTransformer`; create safe fold-local pipelines; warn when opaque/custom code cannot be verified.
5. **Evaluation:** random/stratified, group-aware, or chronological holdout; task-aware classification/regression metrics; original-versus-safer comparison, metric direction, and ablations subject to limits.
6. **Reporting and UI:** interpretable rule-based risk aggregation, Markdown/HTML report, API/CLI, Streamlit dashboard, reproducible synthetic datasets, and integration tests.

## Deterministic vs heuristic

| Deterministic when inputs are supplied | Heuristic / requires human validation |
|---|---|
| Exact duplicate rows; declared group overlap; parsed time ordering; train/test index overlap; pipeline topology for supported sklearn objects; actual rerun metrics | Near-duplicates; possible IDs/groups; suspicious feature names; unusually predictive features; feature legitimacy; intended inference scenario; opaque/custom pipeline behavior |

## Guardrails

- Never alter an uploaded dataset in place.
- Mark sampled/omitted expensive analyses.
- Report risk score as an interpretable priority score, not probability.
- Preserve original results where possible and label alternative evaluation as leakage-safe/safer under declared assumptions.
- Run unit tests after each module and integration/UI smoke tests before handoff.
