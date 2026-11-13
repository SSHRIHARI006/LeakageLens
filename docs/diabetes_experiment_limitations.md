# Diabetes experiment limitations

- The source file has no valid admission timestamp, so temporal validation is unsupported for this case study.
- `readmitted` is an outcome label and the binary target maps both `>30` and `NO` to the negative class for the specific 30-day task.
- Patient-grouped splitting uses an unstratified `GroupShuffleSplit`; class proportions can differ by seed.
- Near-duplicate detection is rounded/normalized row equality candidate detection, not general similarity search.
- The dataset is historical, de-identified and from 130 US hospitals; results do not establish performance or leakage prevalence in other settings.
- Identifier experiments and preprocessing-leakage controls are represented by detector controls, not promoted as clinically valid models.
