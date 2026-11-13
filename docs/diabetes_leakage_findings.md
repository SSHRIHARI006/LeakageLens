# Diabetes leakage findings

The corrected summary is `validation/real_world/diabetes_130/results/run_20261113T122123Z/duplicate_and_detector_summary.json`. Duplicate and near-duplicate comparisons use only scenario predictive features; identifiers and both raw/derived targets are excluded.

- Admission exact predictive-feature duplicates: 31719 rows in 9037 groups.
- Discharge exact predictive-feature duplicates: 0 rows in 0 groups.
- Admission near-duplicate candidates: 31030 rows.
- Discharge near-duplicate candidates: 0 rows.
- Random patient overlap is deterministic split evidence; grouped splits have zero overlap.
- Suspicious-feature warnings are heuristic review signals, not leakage proof.

Controlled validation outputs are in `validation/real_world/diabetes_130/results/run_20261113T122123Z/controlled_validation.json`; they are not used as real-world prevalence claims.
