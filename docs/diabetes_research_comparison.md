# Diabetes research comparison

The dataset provenance and task definition were checked against the [UCI dataset record](https://archive.ics.uci.edu/dataset/296/diabetes%2B130-us%2Bhospitals%2Bfor%2Byears%2B1999-2008), which describes ten years of care at 130 US hospitals and early readmission within 30 days as the task.

The experiment was informed by three project-relevant studies:

- Emi-Johnson and Nkrumah, *Predicting 30-Day Hospital Readmission in Patients With Diabetes Using Machine Learning on Electronic Health Record Data* (2025), consulted through the [PubMed record](https://pubmed.ncbi.nlm.nih.gov/40385730/). Its conventional row-level modeling direction motivated the random-split comparison, but this experiment adds patient-grouped evaluation and explicit prediction-time feature policies.
- Afridi et al., *A Robust and Explainable Framework for Predicting Hospital Readmission in Patients with Diabetes* (2026), [Diabetology](https://www.mdpi.com/2673-4540/7/10/197). Its patient-level partitioning emphasis motivated the `patient_nbr` grouped protocol; this run uses a simpler, reproducible model set without reproducing its explainability or resampling claims.
- Salim and Ibrahim, *A Machine Learning Approach for Predicting 30-Day Hospital Readmission in Patients with Diabetes* (2026), [Healthcare](https://www.mdpi.com/2227-9032/14/9/1185). Its repeated evaluation/calibration direction motivated repeated seeds and threshold-independent metrics; this run does not claim to reproduce its calibration or nested-validation results.

These papers are comparison context, not independent validation of LeakageLens. The case study's conclusions are limited to the supplied dataset, executed configurations and recorded environment.
