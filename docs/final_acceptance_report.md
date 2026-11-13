# LeakageLens final acceptance report

Date: 2026-11-13  
Environment: Python 3.14.4, Linux, commit `2e81972c8a971d66097b32b0717edbd3de848366`

## Status summary

LeakageLens is functionally strong in the core Python path and has reproducible
synthetic benchmark evidence. It does not yet satisfy the full release
acceptance criteria because UI, Ruff, Parquet, and API TestClient validation
remain environment-blocked.

## Implemented and tested

- Ingestion and dataframe validation, including verified legacy `.xls` round-trip.
- Exact, near-duplicate, group, temporal, and feature-suspicion detectors.
- Random, group, duplicate-aware, and chronological split invariants.
- Fold-local estimator fitting and target exclusion.
- Classification/regression metrics, scoring, inflation metadata, reports, and JSON serialization.
- Core unit/regression evidence: **143 passed, 1 skipped**.
- Validation and functional collection: **53 passed, 1 skipped**.
- Non-API integration evidence: **18 passed**.

## Implemented but not fully validated

- FastAPI health/audit behavior: the endpoint works in direct execution, but
  pytest’s local TestClient transport hung on requests and API tests are not
  counted as passing.
- Streamlit UI behavior: app code and smoke tests exist, but Streamlit could
  not be installed in this environment.
- Parquet ingestion and large Parquet performance: PyArrow was unavailable.
- Ruff lint: Ruff could not be downloaded.

## Partially implemented

- Pipeline auditing verifies sklearn compatibility and fold-local execution; it
  is not historical notebook/preprocessing/SMOTE introspection.
- Near-duplicate detection is rounded/normalized row-equality candidate
  detection, not general similarity search.
- Performance evidence covers CSV/XLSX and near-duplicate timing for 1k–10k
  rows; it is not a full resource matrix.

## Unsupported by design

- Arbitrary Python/notebook semantic history.
- Automatic detection of preprocessing or SMOTE performed before upload.
- Calibrated probability of leakage.
- Causal attribution of every original-vs-safer metric difference.

## Synthetic benchmark

Executed commands:

```text
python -m validation.run_benchmark --seeds 10 --output validation/results
python -m validation.summarize_results --input validation/results --output docs/validation_results.md
```

Run directory: `validation/results/run_20261113T102231Z/`  
Records: 960  
Seeds: 42–51

| Detector | TP | FP | FN | TN | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Exact duplicate label conflict | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 1.000 |
| Exact duplicate split contamination | 20 | 0 | 0 | 140 | 1.000 | 1.000 | 1.000 | 1.000 |
| Feature target-proxy warning | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 1.000 |
| Group overlap | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 1.000 |
| Near-duplicate candidates | 30 | 8 | 0 | 122 | 0.789 | 1.000 | 0.938 | 0.882 |
| Temporal violation | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 1.000 |

Near-duplicate false positives are retained as measured heuristic behavior, not
hidden.

## Acceptance blockers

1. Re-run API tests in a clean supported environment with a working
   FastAPI/Starlette/httpx/AnyIO combination.
2. Install Streamlit and execute upload/configuration/report-download flows.
3. Install Ruff and PyArrow; run lint and Parquet tests.
4. Execute the full suite in that clean environment and record one final
   aggregate pass/fail/skip count.

## Spec 2 real-world acceptance status

Implemented and executed:

- Dataset verification, SHA-256 capture, target construction and raw-data preservation.
- Ten-seed random and patient-grouped evaluation for admission-time and discharge-time policies.
- Dummy, logistic, decision tree, random forest and HistGradientBoosting models with fold-local preprocessing.
- Independent patient-overlap, duplicate and detector checks.
- Controlled clean/injected detector validation, with raw expected-versus-observed outcomes.
- Aggregate reports and five publication-style figures.
- Three small-fixture regression tests for target/identifier policy, grouped split invariants and exact cross-split detection.

Not fully validated or unsupported for this case study:

- Temporal validation: unsupported because no defensible admission timestamp exists in the supplied file.
- Full UI/API acceptance remains blocked by the environment limitations listed above.
- Identifier-containing predictive models and preprocessing-leakage injections were not promoted as clinically valid results; they remain controlled diagnostic scope.

Real-world artifacts: `validation/real_world/diabetes_130/results/run_20261113T122123Z/`. Reports: `docs/real_world_case_study_diabetes.md`, `docs/diabetes_experiment_methodology.md`, `docs/diabetes_leakage_findings.md`, `docs/diabetes_model_evaluation.md`, `docs/diabetes_experiment_limitations.md`, and `docs/diabetes_experiment_reproduction.md`.
