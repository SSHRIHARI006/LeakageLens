# Diabetes leakage findings

The independent duplicate and detector summary is `validation/real_world/diabetes_130/results/run_20261113T111348Z/duplicate_and_detector_summary.json`. It records zero full duplicate rows, random-split patient overlap, detector near-duplicate candidates, and heuristic suspicious-feature warnings without exposing row-level records.

The strongest deterministic finding is patient reuse across conventional random row splits. Patient-grouped splits have zero group overlap. Exact duplicate contamination was not observed in the raw dataset. Near-duplicate findings are candidate warnings under LeakageLens's documented rounded/normalized equality semantics and require clinical review.

The controlled validation outcomes are in `validation/real_world/diabetes_130/results/run_20261113T111348Z/controlled_validation.json`; all five controls matched their expected detector outcome in the executed run.
