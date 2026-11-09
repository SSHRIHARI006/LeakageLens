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

```powershell
python -m pip install -r requirements.txt
python examples/generate_datasets.py
streamlit run ui/streamlit_app.py
```

Run the API:

```powershell
uvicorn leakagelens.api:app --reload
```

Run tests:

```powershell
pytest -q
```

## Python API

```python
from leakagelens import LeakageLens, AuditConfig

result = LeakageLens(AuditConfig(
    target="target", task="classification", group_column="customer_id"
)).audit_file("data/group_leakage.csv")
print(result.risk_score, result.inflation)
```

## Limitations

Near duplicates, feature legitimacy, ID candidates, and post-outcome status need domain validation. Current static pipeline support is intentionally conservative; arbitrary Python/notebooks, SMOTE history, spatial semantics, and external validation are not automatically proven. The dashboard does not mutate uploaded data.
