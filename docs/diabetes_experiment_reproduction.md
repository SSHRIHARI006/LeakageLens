# Diabetes 130-US Hospitals reproduction

Run directory: `validation/real_world/diabetes_130/results/run_20261113T122123Z`

Raw dataset: `diabetes+130-us+hospitals+for+years+1999-2008/diabetic_data.csv`

SHA-256: `0689e7ec031237dc63031b938805c48377748761a3b26acab621567afa24df97`

Committed Git SHA recorded by the run: `e686f1a88329addf544b8cd31caff12a12f9d7b9`

Experiment script SHA-256: `67ae0b050f8658809a35ad9d36195da3be1efe5ee1dd37a39400104c4f3eb5ac`

## Command

```text
.venv_sys/bin/python -m validation.real_world.diabetes_130.run_experiment --seeds 10
.venv_sys/bin/python -m validation.real_world.diabetes_130.generate_reports
```

The run uses seeds 42–51, target `readmitted_within_30_days = (readmitted == '<30')`, patient-grouped splits using `patient_nbr`, and excludes `encounter_id` and `patient_nbr` from primary models. Raw seed-level and aggregate outputs, detector summaries, controls, provenance, and figures are preserved in the run directory.
