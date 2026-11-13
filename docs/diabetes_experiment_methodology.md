# Diabetes experiment methodology

The experiment uses fold-local sklearn `ColumnTransformer` and `Pipeline` objects. Numeric features use median imputation; categorical features use most-frequent imputation. Logistic regression uses one-hot encoding and scaling; tree models use ordinal encoding. Class weighting is used where supported. No resampling or test-set tuning is performed.

Models are DummyClassifier, LogisticRegression, DecisionTreeClassifier, RandomForestClassifier and HistGradientBoostingClassifier. Metrics are accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, average precision, specificity and confusion matrices. Random splits are stratified row splits; grouped splits use `GroupShuffleSplit` on `patient_nbr`. Ten seeds (42–51) were executed.

Admission policy excludes `diag_2`, `diag_3`, and `number_diagnoses` because their admission-time availability is unresolved in the distributed data. Raw seed-level results are in `validation/real_world/diabetes_130/results/run_20261113T122123Z/model_results.csv`; aggregate results are in `validation/real_world/diabetes_130/results/run_20261113T122123Z/model_summary.csv`.
