# LeakageLens synthetic benchmark results

Generated from `validation/results/run_20261113T102231Z`. Every number below was produced by running the benchmark code; no result is hand-entered.

## Run metadata

- run id: `run_20261113T102231Z`
- created (UTC): 2026-11-13T10:22:46.814456+00:00
- Python: 3.14.4
- platform: Linux-7.0.0-43-generic-x86_64-with-glibc2.43
- families: SYN-00, SYN-01, SYN-02, SYN-03, SYN-04, SYN-05, SYN-06, SYN-07, SYN-08, SYN-09, SYN-10, SYN-11, SYN-12, SYN-13, SYN-14, SYN-15, SYN-16
- seeds per family: 10 (42–51)

## Per-detector confusion matrix and metrics

| Detector | TP | FP | FN | TN | Precision | Recall | Specificity | FPR | FNR | F1 | Count accuracy | Mean runtime (ms) | Errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `exact_duplicates.label_conflict` | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | undefined (0) | 2.4 | 0 |
| `exact_duplicates.split_contamination` | 20 | 0 | 0 | 140 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 (10) | 2.4 | 0 |
| `feature_suspicion.target_proxy` | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | undefined (0) | 5.0 | 0 |
| `group_overlap.group` | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 (10) | 0.0 | 0 |
| `near_duplicates.near_duplicate` | 30 | 8 | 0 | 122 | 0.789 | 1.000 | 0.938 | 0.062 | 0.000 | 0.882 | 1.000 (20) | 1.1 | 0 |
| `temporal.temporal` | 10 | 0 | 0 | 150 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 (10) | 0.1 | 0 |

`undefined` means the denominator was zero, not a perfect score. Precision/recall over heuristic feature warnings are warning precision/recall, not leakage proof.

## Multiple-seed stability

| Detector | Seeds | Overall accuracy | Mean ± std | Median [IQR] | 95% CI (normal approx.) |
|---|---|---|---|---|---|
| `exact_duplicates.split_contamination` | 10 | 1.000 | 1.000 ± 0.000 | 1.000 [1.000, 1.000] | [1.0, 1.0] |
| `exact_duplicates.label_conflict` | 10 | 1.000 | 1.000 ± 0.000 | 1.000 [1.000, 1.000] | [1.0, 1.0] |
| `group_overlap.group` | 10 | 1.000 | 1.000 ± 0.000 | 1.000 [1.000, 1.000] | [1.0, 1.0] |
| `temporal.temporal` | 10 | 1.000 | 1.000 ± 0.000 | 1.000 [1.000, 1.000] | [1.0, 1.0] |
| `near_duplicates.near_duplicate` | 10 | 0.950 | 0.950 ± 0.025 | 0.938 [0.938, 0.938] | [0.9345, 0.9655] |
| `feature_suspicion.target_proxy` | 10 | 1.000 | 1.000 ± 0.000 | 1.000 [1.000, 1.000] | [1.0, 1.0] |

## Per-family outcomes

| Family | Expected | Detected | Detector | Seed |
|---|---|---|---|---|
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 42 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 42 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 43 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 43 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 44 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 44 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 45 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 45 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 46 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 46 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 47 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 47 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 48 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 48 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 49 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 49 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 50 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 50 |
| SYN-01 | True | True | `exact_duplicates.split_contamination` | 51 |
| SYN-01 | True | True | `near_duplicates.near_duplicate` | 51 |
| SYN-02 | True | True | `group_overlap.group` | 42 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 42 |
| SYN-02 | True | True | `group_overlap.group` | 43 |
| SYN-02 | True | True | `group_overlap.group` | 44 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 44 |
| SYN-02 | True | True | `group_overlap.group` | 45 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 45 |
| SYN-02 | True | True | `group_overlap.group` | 46 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 46 |
| SYN-02 | True | True | `group_overlap.group` | 47 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 47 |
| SYN-02 | True | True | `group_overlap.group` | 48 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 48 |
| SYN-02 | True | True | `group_overlap.group` | 49 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 49 |
| SYN-02 | True | True | `group_overlap.group` | 50 |
| SYN-02 | False | True | `near_duplicates.near_duplicate` | 50 |
| SYN-02 | True | True | `group_overlap.group` | 51 |
| SYN-03 | True | True | `temporal.temporal` | 42 |
| SYN-03 | True | True | `temporal.temporal` | 43 |
| SYN-03 | True | True | `temporal.temporal` | 44 |
| SYN-03 | True | True | `temporal.temporal` | 45 |
| SYN-03 | True | True | `temporal.temporal` | 46 |
| SYN-03 | True | True | `temporal.temporal` | 47 |
| SYN-03 | True | True | `temporal.temporal` | 48 |
| SYN-03 | True | True | `temporal.temporal` | 49 |
| SYN-03 | True | True | `temporal.temporal` | 50 |
| SYN-03 | True | True | `temporal.temporal` | 51 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 42 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 43 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 44 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 45 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 46 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 47 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 48 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 49 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 50 |
| SYN-04 | True | True | `feature_suspicion.target_proxy` | 51 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 42 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 43 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 44 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 45 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 46 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 47 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 48 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 49 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 50 |
| SYN-06 | True | True | `near_duplicates.near_duplicate` | 51 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 42 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 42 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 42 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 43 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 43 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 43 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 44 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 44 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 44 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 45 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 45 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 45 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 46 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 46 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 46 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 47 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 47 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 47 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 48 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 48 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 48 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 49 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 49 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 49 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 50 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 50 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 50 |
| SYN-12 | True | True | `exact_duplicates.split_contamination` | 51 |
| SYN-12 | True | True | `exact_duplicates.label_conflict` | 51 |
| SYN-12 | True | True | `near_duplicates.near_duplicate` | 51 |

## Original versus safer evaluation (observed protocol differences)

- SYN-00 seed 42: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 43: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 44: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 45: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 46: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 47: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 48: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 49: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 50: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-00 seed 51: original `random` vs safer `random`; rows fixed = `True`; deltas: accuracy +0.0000, precision +0.0000, recall +0.0000, f1 +0.0000
- SYN-01 seed 42: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.1671, precision +0.2083, recall +0.1265, f1 +0.1807
- SYN-01 seed 43: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.1421, precision -0.0139, recall +0.1624, f1 +0.0963
- SYN-01 seed 44: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.0605, precision +0.0952, recall +0.0941, f1 +0.0948
- SYN-01 seed 45: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.1754, precision +0.2333, recall +0.0702, f1 +0.1406
- SYN-01 seed 46: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.3406, precision +0.2500, recall +0.4447, f1 +0.3575
- SYN-01 seed 47: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.1632, precision +0.1074, recall +0.3626, f1 +0.2249
- SYN-01 seed 48: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.3876, precision +0.3750, recall +0.3889, f1 +0.3860
- SYN-01 seed 49: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.0619, precision -0.0556, recall +0.2231, f1 +0.0775
- SYN-01 seed 50: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.1166, precision +0.1250, recall +0.1111, f1 +0.1177
- SYN-01 seed 51: original `random` vs safer `duplicate_group`; rows fixed = `False`; deltas: accuracy +0.0868, precision +0.1696, recall +0.1222, f1 +0.1440
- SYN-02 seed 42: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy -0.0484, precision +0.0215, recall -0.2532, f1 -0.1172
- SYN-02 seed 43: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy +0.1000, precision +0.0748, recall +0.1183, f1 +0.0952
- SYN-02 seed 44: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy +0.1500, precision +0.2176, recall +0.1217, f1 +0.1722
- SYN-02 seed 45: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy -0.1011, precision -0.1452, recall +0.0460, f1 -0.0333
- SYN-02 seed 46: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy -0.0312, precision -0.0625, recall +0.0035, f1 -0.0276
- SYN-02 seed 47: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy -0.1000, precision -0.1195, recall -0.0978, f1 -0.1079
- SYN-02 seed 48: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy -0.0548, precision -0.0366, recall -0.0259, f1 -0.0318
- SYN-02 seed 49: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy +0.0688, precision +0.0655, recall +0.0391, f1 +0.0536
- SYN-02 seed 50: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy +0.0167, precision -0.0667, recall +0.1542, f1 +0.0703
- SYN-02 seed 51: original `random` vs safer `group`; rows fixed = `False`; deltas: accuracy -0.1135, precision -0.0915, recall -0.2684, f1 -0.1718
- SYN-03 seed 42: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.2500, precision -0.3175, recall -0.1619, f1 -0.2351
- SYN-03 seed 43: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.1000, precision -0.3091, recall +0.1238, f1 -0.0250
- SYN-03 seed 44: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.0750, precision -0.2575, recall +0.1682, f1 -0.0339
- SYN-03 seed 45: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1500, precision +0.1691, recall -0.2000, f1 +0.0252
- SYN-03 seed 46: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.0000, precision +0.0909, recall -0.1625, f1 +0.0000
- SYN-03 seed 47: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1000, precision +0.2235, recall -0.1333, f1 +0.0591
- SYN-03 seed 48: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1000, precision +0.2619, recall +0.0308, f1 +0.1744
- SYN-03 seed 49: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.0750, precision +0.1649, recall -0.2750, f1 +0.0067
- SYN-03 seed 50: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1000, precision +0.0158, recall +0.1348, f1 +0.0809
- SYN-03 seed 51: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.2250, precision -0.2941, recall -0.2143, f1 -0.2489
- SYN-14 seed 42: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.2500, precision -0.3175, recall -0.1619, f1 -0.2351
- SYN-14 seed 43: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.1000, precision -0.3091, recall +0.1238, f1 -0.0250
- SYN-14 seed 44: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.0750, precision -0.2575, recall +0.1682, f1 -0.0339
- SYN-14 seed 45: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1500, precision +0.1691, recall -0.2000, f1 +0.0252
- SYN-14 seed 46: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.0000, precision +0.0909, recall -0.1625, f1 +0.0000
- SYN-14 seed 47: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1000, precision +0.2235, recall -0.1333, f1 +0.0591
- SYN-14 seed 48: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1000, precision +0.2619, recall +0.0308, f1 +0.1744
- SYN-14 seed 49: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.0750, precision +0.1649, recall -0.2750, f1 +0.0067
- SYN-14 seed 50: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy +0.1000, precision +0.0158, recall +0.1348, f1 +0.0809
- SYN-14 seed 51: original `random` vs safer `chronological`; rows fixed = `False`; deltas: accuracy -0.2250, precision -0.2941, recall -0.2143, f1 -0.2489

## Caveats

- Synthetic families are constructed by the same project; they are not an independent benchmark.
- Risk thresholds were not tuned on these results; the score is a triage heuristic, not a probability.
- Original-vs-safer comparisons with different split strategies change the evaluated population; they are observed protocol differences, not causal leakage inflation.
- A skipped family or metric is not a pass.

- Skipped: SYN-16 — Invalid-input family is covered by unit/integration tests, not the detector benchmark.

See [validation_methodology.md](validation_methodology.md) for the protocol and [known_limitations.md](known_limitations.md) for scope.
