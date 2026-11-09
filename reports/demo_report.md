# LeakageLens audit report

## Executive summary

Leakage risk score: **57.8/100 (HIGH)**. This is an interpretable priority score, not a probability or proof of leakage.

## Dataset

- rows: 240
- columns: 5
- constant_columns: []
- possible_id_columns: []

## Findings

### Declared entity groups cross the split
- Detector: group_overlap
- Severity / confidence: critical / high
- Verification: deterministic
- Evidence: {'shared_groups': 40, 'affected_test_rows': 54, 'percent_test_rows': 90.0}
- Recommendation: Use a group-aware split if deployment requires generalization to new entities.

### No pipeline supplied
- Detector: pipeline_audit
- Severity / confidence: low / low
- Verification: unable_to_determine
- Evidence: {}
- Recommendation: Supply a scikit-learn Pipeline for structural inspection.

## Original versus safer evaluation

Performance differences are protocol-specific and are not asserted as a true-score correction.

- accuracy: original 0.78333, safer 0.81667, observed inflation -0.03334.
- precision: original 0.79412, safer 0.87179, observed inflation -0.07767.
- recall: original 0.81818, safer 0.85, observed inflation -0.03182.
- f1: original 0.80597, safer 0.86076, observed inflation -0.05479.

## Reproducibility

{'seed': 42, 'task': 'classification', 'target': 'target', 'original_strategy': 'random', 'group_column': 'customer_id', 'time_column': None}

## Limitations

Feature legitimacy and deployment semantics require domain validation. Near-duplicate and feature warnings are heuristic; unsupported pipelines cannot be fully inspected.