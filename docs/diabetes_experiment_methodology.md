# Diabetes experiment methodology

The experiment uses a fold-local `ColumnTransformer` and sklearn `Pipeline`. Numeric features use median imputation; categorical features use most-frequent imputation. Logistic regression uses one-hot encoding and scaling; tree models use ordinal encoding without scaling. Class weighting is used where supported; no resampling or test-set tuning is performed.

Models: DummyClassifier, LogisticRegression, DecisionTreeClassifier, RandomForestClassifier and HistGradientBoostingClassifier. Metrics: accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, average precision, specificity and 2×2 confusion matrices.

The random protocol uses stratified row splitting. The patient-grouped protocol uses `GroupShuffleSplit` on `patient_nbr`; class-distribution differences are reported rather than hidden. The run uses seeds 42–51.

The admission/discharge feature policies are explicit and are not directly comparable as one clinical task. No chronological experiment is reported because the available file lacks a defensible timestamp.

Raw seed-level results are in `validation/real_world/diabetes_130/results/run_20261113T111348Z/model_results.csv`; aggregate mean, standard deviation, minimum and maximum are in `model_summary.csv`.
