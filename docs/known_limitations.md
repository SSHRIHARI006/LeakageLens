# Known limitations

These limitations are part of the result, not an afterthought. Findings are
evidence-backed risks, and the risk score is a triage heuristic, not a
probability that leakage exists.

## Detection scope

- **Near duplicates are not similarity search.** The detector rounds numeric
  values to two decimals, strips and lowercases categorical text, and reports rows
  that become equal. It does not use embeddings, edit distance, or nearest
  neighbours, and it reports candidates rather than confirmed duplicates.
- **Sampling.** Near-duplicate analysis uses at most the first 100,000 rows when
  the dataset is larger; findings say that analysis was sampled.
- **Feature suspicion is heuristic.** Name matches and mutual information are
  warnings, not proof. A legitimate strong predictor can trigger the association
  warning; a target-derived feature with an innocuous name can be missed. Only
  numeric predictors are screened for association; categorical coverage is
  recorded but not scored.
- **Exact duplicates hash all non-target columns.** Two rows that differ only in
  the target are reported as duplicate features and separately as a label
  conflict; they are not treated as identical labelled examples.

## Split and evaluation scope

- **Group split requires enough groups.** With very few groups, a non-empty test
  partition cannot be formed and the split raises a clear error rather than
  silently degrading. Null group values are excluded from overlap counting.
- **Temporal checks require the temporal scenario and a parseable time column.**
  A date column alone is not temporal leakage. Unparseable timestamps are
  excluded from the chronology comparison and reported.
- **Safer evaluations can change the evaluated population.** When the safer split
  scores different test rows, metric differences are observed protocol
  differences, not a causal estimate of inflation.
- **The default model is fixed.** Metrics depend on the default random forest and
  on the provided seed; they are not a model-selection benchmark.

## Pipeline and deployment scope

- **No arbitrary pipeline introspection.** The pipeline audit verifies that an
  object can be cloned and fit/predict inside LeakageLens. Historical preprocessing
  performed before upload, notebook state, resampling history, and external joins
  are not reconstructed.
- **HTTP audits reject pipelines.** The API accepts data only and uses the default
  pipeline; deserializing arbitrary Python objects from a request would be unsafe.
- **The dashboard does not select custom pipelines.** It exposes the default
  pipeline and core configuration only.
- **In-memory processing.** Uploaded data is written to a temporary file for
  suffix-aware loading and removed afterwards; the tool is not designed for
  datasets that exceed available memory.

## Validation scope

- **Synthetic families are project-authored.** They exercise the intended
  mechanisms and matched negative controls, but they are not an independent or
  real-world benchmark.
- **Thresholds are not calibrated.** Severity floors and the risk score were set
  as interpretable heuristics, not fitted to validation data.
- **Skipped checks are not passes.** Optional format tests skip when their reader
  is unavailable, and benchmark families that do not declare a detector outcome
  are excluded from that detector's score rather than counted as correct.
- **No claim of completeness.** Spatial leakage, leakage through external data
  sources, and semantic target proxies that neither names nor numeric association
  reveal are outside the current detection scope.

- **Environment-specific UI/API validation.** Core, validation, and non-API
  integration layers were executed. Streamlit/Ruff/PyArrow could not be
  installed because the package mirror stalled on large wheels, and the local
  Python 3.14 Starlette/AnyIO TestClient transport hung on API requests. These
  are outstanding validation blockers, not passing results.
