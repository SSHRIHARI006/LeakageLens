# Diabetes model evaluation

Run: `validation/real_world/diabetes_130/results/run_20261113T111348Z`

Admission-time primary grouped results (mean ± SD over 10 seeds):

| Model | ROC-AUC | AP | F1 | Balanced accuracy |
|---|---:|---:|---:|---:|
| dummy | 0.500 ± 0.000 | 0.112 ± 0.003 | 0.000 ± 0.000 | 0.500 ± 0.000 |
| forest | 0.618 ± 0.006 | 0.175 ± 0.008 | 0.215 ± 0.009 | 0.558 ± 0.005 |
| hist_gradient_boosting | 0.645 ± 0.004 | 0.203 ± 0.009 | 0.013 ± 0.003 | 0.503 ± 0.001 |
| logistic | 0.631 ± 0.006 | 0.193 ± 0.006 | 0.250 ± 0.006 | 0.595 ± 0.005 |
| tree | 0.595 ± 0.004 | 0.162 ± 0.008 | 0.231 ± 0.006 | 0.573 ± 0.004 |

Random and grouped values answer different deployment questions. The raw per-seed table includes both scenarios and both protocols.
