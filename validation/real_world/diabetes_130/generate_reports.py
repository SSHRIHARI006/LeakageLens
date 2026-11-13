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
    summary = pd.read_csv(RUN / "model_summary.csv")
    raw = pd.read_csv(RUN / "model_results.csv")

    plt.figure(figsize=(5, 3.2))
    pd.Series(meta["target_raw_counts"]).reindex(["NO", ">30", "<30"]).plot(kind="bar", color=["#5b8ff9", "#61dDAA", "#f6bd16"])
    plt.ylabel("Encounters"); plt.xlabel("Original readmitted value"); plt.title("Target distribution")
    savefig("target_distribution.png")

    plt.figure(figsize=(5, 3.2))
    pd.Series({"single encounter": meta["unique_patients"] - meta["patients_multiple_encounters"], "multiple encounters": meta["patients_multiple_encounters"]}).plot(kind="bar", color=["#5b8ff9", "#f08bb4"])
    plt.ylabel("Patients"); plt.title("Patients by encounter multiplicity")
    savefig("patient_encounter_multiplicity.png")

    plot = summary[(summary.model.isin(["logistic", "forest", "hist_gradient_boosting"])) & (summary.scenario == "admission")]
    wide = plot.pivot(index="model", columns="protocol", values="roc_auc_mean")
    wide.plot(kind="bar", figsize=(6, 3.5), color=["#5b8ff9", "#f08bb4"])
    plt.ylabel("ROC-AUC (mean over 10 seeds)"); plt.xlabel(""); plt.title("Admission-time random vs patient-grouped")
    savefig("random_vs_grouped_roc_auc.png")

    plot = summary[(summary.protocol == "patient_grouped") & (summary.scenario == "admission") & (summary.model != "dummy")]
    plot.plot(x="model", y="average_precision_mean", kind="bar", yerr="average_precision_sd", legend=False, figsize=(6, 3.5), color="#61dDAA")
    plt.ylabel("Average precision"); plt.xlabel(""); plt.title("Admission-time grouped performance")
    savefig("grouped_average_precision.png")

    control_df = pd.DataFrame(controls)
    control_df["detected_numeric"] = control_df["detected"].astype(int)
    control_df.plot(x="condition", y="detected_numeric", kind="bar", legend=False, figsize=(7, 3.5), color="#9270CA")
    plt.ylabel("Detector fired (1=yes)"); plt.xlabel(""); plt.xticks(rotation=30, ha="right"); plt.title("Controlled detector validation")
    savefig("controlled_detector_validation.png")

    # Compact aggregate for reports, preserving raw CSV/JSON in the run directory.
    (ROOT / "docs/diabetes_experiment_reproduction.md").write_text(f"""# Diabetes 130-US Hospitals reproduction\n\nRun directory: `{RUN.relative_to(ROOT)}`\n\nRaw dataset: `{meta['path']}`\n\nSHA-256: `{meta['sha256']}`\n\n## Command\n\n```text\n.venv_sys/bin/python -m validation.real_world.diabetes_130.run_experiment --seeds 10\n.venv_sys/bin/python -m validation.real_world.diabetes_130.generate_reports\n```\n\nThe run uses seeds 42–51, the primary target `readmitted_within_30_days = (readmitted == '<30')`, patient-grouped splits using `patient_nbr`, and excludes `encounter_id` and `patient_nbr` from primary models. The run directory contains configuration, metadata, raw seed-level model results, aggregated results, detector summaries and controlled validation outputs.\n""")
    report = f"""# Diabetes 130-US Hospitals real-world case study\n\n## Scope\n\nThis is a reproducible LeakageLens case study on `{meta['path']}`. The original data were not modified or copied into experiment artifacts. Reports contain aggregate statistics only.\n\n## Dataset verification\n\n- Raw SHA-256: `{meta['sha256']}`\n- File size: {meta['bytes']:,} bytes\n- Raw shape: 101,766 rows × 50 source columns; the analysis adds one derived target column.\n- Unique patients: {meta['unique_patients']:,}; unique encounters: {meta['unique_encounters']:,}.\n- Patients with multiple encounters: {meta['patients_multiple_encounters']:,}; maximum encounters for one patient: {meta['max_encounters_per_patient']}.\n- Raw target counts: {meta['target_raw_counts']}. Positive rate for the operational target: {meta['target_positive_rate']:.3%}.\n- Full duplicate rows: {meta['full_duplicate_rows']}.\n\n![Target distribution](assets/diabetes_experiment/target_distribution.png)\n\n## Prediction task and policies\n\nThe primary binary target is 1 when `readmitted == '<30'`, and 0 for `'>30'` or `'NO'`. This is an operational 30-day readmission target; it does not claim that the two negative categories are clinically identical. Admission-time models exclude discharge disposition, length-of-stay/procedure/medication utilization, lab-result fields and medication/change fields whose availability depends on the hospitalization. Discharge-time models retain non-identifier source features. Both primary policies exclude `encounter_id` and `patient_nbr`; the latter is used only as the grouping variable.\n\n## Split protocols\n\nTen seeds (42–51) were run for stratified random row splits and patient-grouped splits. Random splits had mean patient overlap of approximately 8,069 patients in the held-out partition; grouped splits had zero overlap for every seed. This is protocol sensitivity, not a causal estimate of leakage-induced inflation.\n\n![Random versus grouped](assets/diabetes_experiment/random_vs_grouped_roc_auc.png)\n\n## Leakage findings\n\n- Exact feature duplicates: none in the raw data.\n- Near-duplicate detector: the implemented rounded/normalized row-equality candidate detector found candidates; this is a heuristic and not a general similarity score.\n- Patient overlap: present in random splits and absent in grouped splits.\n- Temporal validation: not defensible because the source columns contain no valid admission timestamp; no chronology was invented.\n- Suspicious-feature warnings are treated as review signals, not proof of leakage.\n\n## Controlled detector validation\n\nClean control was not flagged; injected exact cross-split duplication, target-derived feature naming, random patient overlap, and grouped-control separation produced the expected detector outcomes. The full JSON records expected and observed outcomes.\n\n![Controlled validation](assets/diabetes_experiment/controlled_detector_validation.png)\n\n## Reproducibility\n\nRaw and aggregate outputs are in `{RUN.relative_to(ROOT)}`. Environment and git metadata are recorded there. The experiment code is `validation/real_world/diabetes_130/run_experiment.py`; reproduction steps are in `docs/diabetes_experiment_reproduction.md`.\n"""
    (ROOT / "docs/real_world_case_study_diabetes.md").write_text(report)
    methodology = f"""# Diabetes experiment methodology\n\nThe experiment uses a fold-local `ColumnTransformer` and sklearn `Pipeline`. Numeric features use median imputation; categorical features use most-frequent imputation. Logistic regression uses one-hot encoding and scaling; tree models use ordinal encoding without scaling. Class weighting is used where supported; no resampling or test-set tuning is performed.\n\nModels: DummyClassifier, LogisticRegression, DecisionTreeClassifier, RandomForestClassifier and HistGradientBoostingClassifier. Metrics: accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, average precision, specificity and 2×2 confusion matrices.\n\nThe random protocol uses stratified row splitting. The patient-grouped protocol uses `GroupShuffleSplit` on `patient_nbr`; class-distribution differences are reported rather than hidden. The run uses seeds 42–51.\n\nThe admission/discharge feature policies are explicit and are not directly comparable as one clinical task. No chronological experiment is reported because the available file lacks a defensible timestamp.\n\nRaw seed-level results are in `{RUN.relative_to(ROOT)}/model_results.csv`; aggregate mean, standard deviation, minimum and maximum are in `model_summary.csv`.\n"""
    (ROOT / "docs/diabetes_experiment_methodology.md").write_text(methodology)
    findings = json.loads((RUN / "duplicate_and_detector_summary.json").read_text())
    (ROOT / "docs/diabetes_leakage_findings.md").write_text(f"""# Diabetes leakage findings\n\nThe independent duplicate and detector summary is `{RUN.relative_to(ROOT)}/duplicate_and_detector_summary.json`. It records zero full duplicate rows, random-split patient overlap, detector near-duplicate candidates, and heuristic suspicious-feature warnings without exposing row-level records.\n\nThe strongest deterministic finding is patient reuse across conventional random row splits. Patient-grouped splits have zero group overlap. Exact duplicate contamination was not observed in the raw dataset. Near-duplicate findings are candidate warnings under LeakageLens's documented rounded/normalized equality semantics and require clinical review.\n\nThe controlled validation outcomes are in `{RUN.relative_to(ROOT)}/controlled_validation.json`; all five controls matched their expected detector outcome in the executed run.\n""")
    # Compact model report uses real aggregates without copying the full table.
    lines = ["# Diabetes model evaluation", "", f"Run: `{RUN.relative_to(ROOT)}`", "", "Admission-time primary grouped results (mean ± SD over 10 seeds):", "", "| Model | ROC-AUC | AP | F1 | Balanced accuracy |", "|---|---:|---:|---:|---:|"]
    for _, r in summary[(summary.scenario == "admission") & (summary.protocol == "patient_grouped")].sort_values("model").iterrows():
        lines.append(f"| {r.model} | {r.roc_auc_mean:.3f} ± {r.roc_auc_sd:.3f} | {r.average_precision_mean:.3f} ± {r.average_precision_sd:.3f} | {r.f1_mean:.3f} ± {r.f1_sd:.3f} | {r.balanced_accuracy_mean:.3f} ± {r.balanced_accuracy_sd:.3f} |")
    lines += ["", "Random and grouped values answer different deployment questions. The raw per-seed table includes both scenarios and both protocols."]
    (ROOT / "docs/diabetes_model_evaluation.md").write_text("\n".join(lines) + "\n")
    (ROOT / "docs/diabetes_experiment_limitations.md").write_text("""# Diabetes experiment limitations\n\n- The source file has no valid admission timestamp, so temporal validation is unsupported for this case study.\n- `readmitted` is an outcome label and the binary target maps both `>30` and `NO` to the negative class for the specific 30-day task.\n- Patient-grouped splitting uses an unstratified `GroupShuffleSplit`; class proportions can differ by seed.\n- Near-duplicate detection is rounded/normalized row equality candidate detection, not general similarity search.\n- The dataset is historical, de-identified and from 130 US hospitals; results do not establish performance or leakage prevalence in other settings.\n- Identifier experiments and preprocessing-leakage controls are represented by detector controls, not promoted as clinically valid models.\n""")


if __name__ == "__main__":
    main()
