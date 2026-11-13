# LeakageLens

LeakageLens is a research-oriented, dataset-agnostic framework for auditing common data-leakage mechanisms in tabular ML and comparing an original evaluation with a safer alternative. It reports evidence, severity, confidence, and recommendations; it does not prove leakage or produce a probability of leakage.

## What is implemented

- CSV, XLSX, and Parquet ingestion with target/data validation and dataset profile.
- Exact duplicate and train/test duplicate-overlap audit.
- Optional entity/group and temporal split audit plus group/chronological safer evaluation.
- Heuristic feature-name and numerical target-association warnings.
- Supported sklearn-compatible pipeline check and fold-local evaluation (a default pipeline is built when none is supplied).
- Classification (accuracy, precision, recall, F1) and regression (MAE, RMSE, R2) comparison with direction-aware observed inflation.
- Interpretable multi-signal risk priority score, Markdown reporting, FastAPI endpoint, Streamlit dashboard, deterministic demo data, and tests.

## Research basis

The supplied-paper inventory, synthesized review, traceable feature mapping, references, and phased plan are preserved in [`docs/`](docs/). The score and UI are project extensions, not literature-validated probabilities.

## Install and run

```bash
python -m pip install -e ".[dev]"
python examples/generate_datasets.py
streamlit run ui/streamlit_app.py
```

Run the API:

```powershell
uvicorn leakagelens.api:app --reload
```

Run tests:

```bash
pytest -q
```

The executable test suite is organized under [`tests/`](tests/), and the
synthetic validation harness is under [`validation/`](validation/). The testing
strategy is documented in [`docs/testing_strategy.md`](docs/testing_strategy.md).

Run the synthetic benchmark and regenerate the validation report:

```bash
python -m validation.run_benchmark --seeds 10 --output validation/results
python -m validation.summarize_results --input validation/results --output docs/validation_results.md
```

The testing layers, synthetic families, and honest reporting rules are documented in
[`docs/testing_strategy.md`](docs/testing_strategy.md), [`docs/validation_methodology.md`](docs/validation_methodology.md),
and [`docs/known_limitations.md`](docs/known_limitations.md).

## Python API

```python
from leakagelens import LeakageLens, AuditConfig

result = LeakageLens(AuditConfig(
    target="target", task="classification", group_column="customer_id"
)).audit_file("data/group_leakage.csv")
print(result.risk_score, result.inflation)
```

## Limitations

Near duplicates, feature legitimacy, ID candidates, and post-outcome status need domain validation. Current static pipeline support is intentionally conservative; arbitrary Python/notebooks, SMOTE history, spatial semantics, and external validation are not automatically proven. The dashboard does not mutate uploaded data. The full list is in [`docs/known_limitations.md`](docs/known_limitations.md).
