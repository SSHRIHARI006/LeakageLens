from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RUN = sorted((ROOT / "validation/real_world/diabetes_130/results").glob("run_*"))[-1]
ASSETS = ROOT / "docs/assets/diabetes_experiment"


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(ASSETS / name, dpi=180, bbox_inches="tight")
    plt.close()


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-leakagelens")
    ASSETS.mkdir(parents=True, exist_ok=True)
    meta = json.loads((RUN / "dataset_metadata.json").read_text())
    controls = json.loads((RUN / "controlled_validation.json").read_text())
    detector_summary = json.loads((RUN / "duplicate_and_detector_summary.json").read_text())
    run_metadata = json.loads((RUN / "run_metadata.json").read_text())
    summary = pd.read_csv(RUN / "model_summary.csv")
    admission = detector_summary["scenarios"]["admission"]
    discharge = detector_summary["scenarios"]["discharge"]

    plt.figure(figsize=(5, 3.2))
    pd.Series(meta["target_raw_counts"]).reindex(["NO", ">30", "<30"]).plot(kind="bar", color=["#5b8ff9", "#61dDAA", "#f6bd16"])
    plt.ylabel("Encounters"); plt.xlabel("Original readmitted value"); plt.title("Target distribution"); savefig("target_distribution.png")
    plt.figure(figsize=(5, 3.2))
    pd.Series({"single encounter": meta["unique_patients"] - meta["patients_multiple_encounters"], "multiple encounters": meta["patients_multiple_encounters"]}).plot(kind="bar", color=["#5b8ff9", "#f08bb4"])
    plt.ylabel("Patients"); plt.title("Patients by encounter multiplicity"); savefig("patient_encounter_multiplicity.png")
    plot = summary[(summary.model.isin(["logistic", "forest", "hist_gradient_boosting"])) & (summary.scenario == "admission")]
    plot.pivot(index="model", columns="protocol", values="roc_auc_mean").plot(kind="bar", figsize=(6, 3.5), color=["#5b8ff9", "#f08bb4"])
    plt.ylabel("ROC-AUC (mean over 10 seeds)"); plt.xlabel(""); plt.title("Admission-time random vs patient-grouped"); savefig("random_vs_grouped_roc_auc.png")
    plot = summary[(summary.protocol == "patient_grouped") & (summary.scenario == "admission") & (summary.model != "dummy")]
    plot.plot(x="model", y="average_precision_mean", kind="bar", yerr="average_precision_sd", legend=False, figsize=(6, 3.5), color="#61dDAA")
    plt.ylabel("Average precision"); plt.xlabel(""); plt.title("Admission-time grouped performance"); savefig("grouped_average_precision.png")
    control_df = pd.DataFrame(controls)
    control_df["detected_numeric"] = control_df["detected"].astype(int)
    control_df.plot(x="condition", y="detected_numeric", kind="bar", legend=False, figsize=(7, 3.5), color="#9270CA")
    plt.ylabel("Detector fired (1=yes)"); plt.xlabel(""); plt.xticks(rotation=30, ha="right"); plt.title("Controlled detector validation"); savefig("controlled_detector_validation.png")

    run = str(RUN.relative_to(ROOT))
    (ROOT / "docs/diabetes_experiment_reproduction.md").write_text(f"""# Diabetes 130-US Hospitals reproduction

Run directory: `{run}`

Raw dataset: `{meta['path']}`

SHA-256: `{meta['sha256']}`

Committed Git SHA recorded by the run: `{run_metadata['git_sha']}`

Experiment script SHA-256: `{run_metadata['experiment_script_sha256']}`

## Command

```text
.venv_sys/bin/python -m validation.real_world.diabetes_130.run_experiment --seeds 10
.venv_sys/bin/python -m validation.real_world.diabetes_130.generate_reports
```

The run uses seeds 42–51, target `readmitted_within_30_days = (readmitted == '<30')`, patient-grouped splits using `patient_nbr`, and excludes `encounter_id` and `patient_nbr` from primary models. Raw seed-level and aggregate outputs, detector summaries, controls, provenance, and figures are preserved in the run directory.
""")

    admission_near = sum(x.get("affected_rows", 0) or 0 for x in admission["near_duplicates"])
    discharge_near = sum(x.get("affected_rows", 0) or 0 for x in discharge["near_duplicates"])
    (ROOT / "docs/real_world_case_study_diabetes.md").write_text(f"""# Diabetes 130-US Hospitals real-world case study

The raw file contains 101,766 encounters and 50 source columns. SHA-256: `{meta['sha256']}`. The binary target is 1 when `readmitted == '<30'`, and 0 for `'>30'` or `'NO'`; this is an operational 30-day target, not a claim that the two negative categories are clinically identical.

## Prediction-time policies

Primary models exclude `encounter_id` and `patient_nbr`; `patient_nbr` is only a grouping variable. Admission-time models exclude discharge disposition, stay/procedure/medication utilization, lab-result fields, medication/change fields, `diag_2`, `diag_3`, and `number_diagnoses`. The distributed data do not establish those secondary diagnoses or final count as known at admission. Discharge-time models retain non-identifier source features.

## Executed evidence

Ten seeds (42–51) were run for random row splits and patient-grouped splits across both policies and five model families. Random splits had approximately 8,069 overlapping patients on average; grouped splits had zero overlap for every seed. This is protocol sensitivity, not causal leakage inflation.

![Random versus grouped](assets/diabetes_experiment/random_vs_grouped_roc_auc.png)

## Corrected duplicate findings

Duplicate comparisons use each scenario's actual predictive features and exclude `encounter_id`, `patient_nbr`, `readmitted`, and the derived target. Admission-time exact duplicates: {admission['exact_feature_duplicates']['rows']} rows in {admission['exact_feature_duplicates']['groups']} groups. Discharge-time exact duplicates: {discharge['exact_feature_duplicates']['rows']} rows in {discharge['exact_feature_duplicates']['groups']} groups. Near-duplicate candidate rows: admission {admission_near}; discharge {discharge_near}. These candidates use LeakageLens's rounded/normalized equality definition and are heuristic, not general similarity scores.

Per-seed train/test predictive-feature overlap is preserved in `duplicate_and_detector_summary.json`. Exact duplicates, near-duplicate candidates, patient overlap, and suspicious-feature warnings are reported separately.

## Other limitations

No temporal result is claimed because the dataset has no defensible admission timestamp. The full duplicate/near-duplicate and controlled-validation outputs are in `{run}`. Figures are generated from the same run's CSV/JSON artifacts.

## Provenance

Committed Git SHA: `{run_metadata['git_sha']}`. Experiment script SHA-256: `{run_metadata['experiment_script_sha256']}`. Dependency versions are in `run_metadata.json`.
""")
    (ROOT / "docs/diabetes_experiment_methodology.md").write_text(f"""# Diabetes experiment methodology

The experiment uses fold-local sklearn `ColumnTransformer` and `Pipeline` objects. Numeric features use median imputation; categorical features use most-frequent imputation. Logistic regression uses one-hot encoding and scaling; tree models use ordinal encoding. Class weighting is used where supported. No resampling or test-set tuning is performed.

Models are DummyClassifier, LogisticRegression, DecisionTreeClassifier, RandomForestClassifier and HistGradientBoostingClassifier. Metrics are accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, average precision, specificity and confusion matrices. Random splits are stratified row splits; grouped splits use `GroupShuffleSplit` on `patient_nbr`. Ten seeds (42–51) were executed.

Admission policy excludes `diag_2`, `diag_3`, and `number_diagnoses` because their admission-time availability is unresolved in the distributed data. Raw seed-level results are in `{run}/model_results.csv`; aggregate results are in `{run}/model_summary.csv`.
""")
    (ROOT / "docs/diabetes_leakage_findings.md").write_text(f"""# Diabetes leakage findings

The corrected summary is `{run}/duplicate_and_detector_summary.json`. Duplicate and near-duplicate comparisons use only scenario predictive features; identifiers and both raw/derived targets are excluded.

- Admission exact predictive-feature duplicates: {admission['exact_feature_duplicates']['rows']} rows in {admission['exact_feature_duplicates']['groups']} groups.
- Discharge exact predictive-feature duplicates: {discharge['exact_feature_duplicates']['rows']} rows in {discharge['exact_feature_duplicates']['groups']} groups.
- Admission near-duplicate candidates: {admission_near} rows.
- Discharge near-duplicate candidates: {discharge_near} rows.
- Random patient overlap is deterministic split evidence; grouped splits have zero overlap.
- Suspicious-feature warnings are heuristic review signals, not leakage proof.

Controlled validation outputs are in `{run}/controlled_validation.json`; they are not used as real-world prevalence claims.
""")
    lines = ["# Diabetes model evaluation", "", f"Run: `{run}`", "", "Admission-time patient-grouped results (mean ± SD over 10 seeds):", "", "| Model | ROC-AUC | AP | F1 | Balanced accuracy |", "|---|---:|---:|---:|---:|"]
    for _, row in summary[(summary.scenario == "admission") & (summary.protocol == "patient_grouped")].sort_values("model").iterrows():
        lines.append(f"| {row.model} | {row.roc_auc_mean:.3f} ± {row.roc_auc_sd:.3f} | {row.average_precision_mean:.3f} ± {row.average_precision_sd:.3f} | {row.f1_mean:.3f} ± {row.f1_sd:.3f} | {row.balanced_accuracy_mean:.3f} ± {row.balanced_accuracy_sd:.3f} |")
    lines += ["", "Random and grouped values answer different deployment questions; the raw per-seed table contains both protocols and both feature policies."]
    (ROOT / "docs/diabetes_model_evaluation.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
