# Diabetes model evaluation

Run: `validation/real_world/diabetes_130/results/run_20261113T122123Z`

Admission-time patient-grouped results (mean ± SD over 10 seeds):

| Model | ROC-AUC | AP | F1 | Balanced accuracy |
|---|---:|---:|---:|---:|
| dummy | 0.500 ± 0.000 | 0.112 ± 0.003 | 0.000 ± 0.000 | 0.500 ± 0.000 |
| forest | 0.611 ± 0.006 | 0.176 ± 0.009 | 0.231 ± 0.008 | 0.569 ± 0.004 |
| hist_gradient_boosting | 0.639 ± 0.005 | 0.201 ± 0.009 | 0.012 ± 0.004 | 0.503 ± 0.001 |
| logistic | 0.634 ± 0.007 | 0.196 ± 0.007 | 0.252 ± 0.007 | 0.597 ± 0.005 |
| tree | 0.602 ± 0.006 | 0.168 ± 0.009 | 0.235 ± 0.008 | 0.577 ± 0.005 |

Random and grouped values answer different deployment questions; the raw per-seed table contains both protocols and both feature policies.
