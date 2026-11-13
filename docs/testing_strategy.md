# Testing strategy

This document describes the executable checks for LeakageLens. It is deliberately
narrower than a claim of correctness: every check below has a real command, and a
skipped test is reported as skipped, never as passed.

## Layers

| Layer | Location | What it asserts |
| --- | --- | --- |
| Unit | `tests/unit/` | Detector contracts, validation errors, split invariants, metric encoding, inflation direction, scoring thresholds, serialization, and Markdown output. |
| Integration | `tests/integration/` | The full audit workflow, safer-split invariants, fold-local fitting, and the HTTP API through `TestClient`. |
| Functional | `tests/functional/` | The Streamlit app loads without an exception and its empty state explains the example data and limitations. |
| Validation | `tests/validation/` | Synthetic family manifests, declared ground truth alignment, negative controls, multi-seed stability, and a real benchmark smoke run. |
| Regression | `tests/regression/` | Defects observed during development: a syntax error in the app, raw `KeyError`s for a missing target, string labels breaking metrics, null/sentinel collisions, and wording that overclaims near-duplicates. |

## Determinism

- Fixtures use fixed seeds or small deterministic dataframes; no test depends on
  wall-clock time, network access, or a random model score.
- The default pipeline uses a fixed `random_state`; split fingerprints are hashes
  of sorted positional indices, so protocol comparisons are reproducible.
- Benchmark runs persist `summary.json`, `config.json`, and per-dataset manifests
  in a timestamped directory so a reported number can be traced to its inputs.
- Tests that need optional formats (`XLSX`, `Parquet`) importorskip their reader;
  the skip is visible in pytest output.

## Commands

```bash
python -m pip install -e ".[dev]"
pytest -q
pytest -q tests/unit
pytest -q tests/integration
python -m validation.run_benchmark --seeds 10 --output validation/results
python -m validation.summarize_results --input validation/results --output docs/validation_results.md
```

## CI

`.github/workflows/ci.yml` runs lint (`ruff`, `compileall`), unit, integration,
functional, benchmark smoke, and an API import check as separate jobs. The
benchmark smoke job uses one seed and a subset of families; it is a wiring check,
not a scientific result.

## Final validation run (2026-11-13)

Executed evidence with Python 3.14.4, pytest 8.4.2, pandas 3.1.1, NumPy 2.3.5,
SciPy 1.16.3, and scikit-learn 1.9.1:

- unit and regression: **143 passed, 1 skipped**;
- validation and functional collection: **53 passed, 1 skipped**; the skip is
  Streamlit because its wheel could not be downloaded;
- non-API integration: **18 passed** after correcting the two-group split guard;
- legacy `.xls` round-trip: **passed** with `xlrd 2.0.2`;
- API TestClient: **not accepted as passed** because the local Python 3.14
  Starlette/AnyIO transport hung on requests.

The first full collection run exposed 22 failures. They were triaged into
fixture/test defects and genuine implementation defects; fixes and regression
coverage remain in the repository.

## What is not covered

- Arbitrary user pipelines and notebook history are not statically audited; the
  pipeline check only verifies fit/predict compatibility and fold-local fitting.
- General nearest-neighbour similarity search is not implemented; near-duplicate
  checks are rounded/normalized row equality.
- The synthetic families are constructed by this project, so benchmark accuracy
  is not an independent generalization estimate.
- The risk thresholds are fixed heuristics and are not calibrated probabilities.
