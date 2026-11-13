# Diabetes 130-US Hospitals reproduction

Run directory: `validation/real_world/diabetes_130/results/run_20261113T111348Z`

Raw dataset: `diabetes+130-us+hospitals+for+years+1999-2008/diabetic_data.csv`

SHA-256: `0689e7ec031237dc63031b938805c48377748761a3b26acab621567afa24df97`

## Command

```text
.venv_sys/bin/python -m validation.real_world.diabetes_130.run_experiment --seeds 10
.venv_sys/bin/python -m validation.real_world.diabetes_130.generate_reports
```

The run uses seeds 42–51, the primary target `readmitted_within_30_days = (readmitted == '<30')`, patient-grouped splits using `patient_nbr`, and excludes `encounter_id` and `patient_nbr` from primary models. The run directory contains configuration, metadata, raw seed-level model results, aggregated results, detector summaries and controlled validation outputs.
