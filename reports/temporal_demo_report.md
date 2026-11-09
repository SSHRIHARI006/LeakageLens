# LeakageLens audit report

## Executive summary

Leakage risk score: **41.2/100 (HIGH)**. This is an interpretable priority score, not a probability or proof of leakage.

## Dataset

- rows: 240
- columns: 5
- constant_columns: []
- possible_id_columns: ['event_date']

## Findings

### Future observations appear in training
- Detector: temporal
- Severity / confidence: high / high
- Verification: deterministic
- Evidence: {'train_max': '2023-08-26 00:00:00', 'test_min': '2023-01-02 00:00:00'}
- Recommendation: For future prediction, use chronological splitting with training dates before test dates.

### No pipeline supplied
- Detector: pipeline_audit
- Severity / confidence: low / low
- Verification: unable_to_determine
- Evidence: {}
- Recommendation: Supply a scikit-learn Pipeline for structural inspection.

## Original versus safer evaluation

Performance differences are protocol-specific and are not asserted as a true-score correction.

- accuracy: original 0.66667, safer 0.68333, observed inflation -0.01666.
- precision: original 0.65789, safer 0.70968, observed inflation -0.05179.
- recall: original 0.78125, safer 0.6875, observed inflation 0.09375.
- f1: original 0.71429, safer 0.69841, observed inflation 0.01588.

## Reproducibility

{'seed': 42, 'task': 'classification', 'target': 'target', 'original_strategy': 'random', 'group_column': None, 'time_column': 'event_date'}

## Limitations

Feature legitimacy and deployment semantics require domain validation. Near-duplicate and feature warnings are heuristic; unsupported pipelines cannot be fully inspected.