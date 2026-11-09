# Research-to-feature mapping

Labels: **Direct** = literature explicitly motivates the behavior; **Adapted** = project applies the idea to general tabular data; **Extension** = our addition; **Engineering** = implementation choice, not a claimed literature contribution.

| LeakageLens feature | Classification | Supporting supplied work | Traceable rationale |
|---|---|---|---|
| Exact row hashes, duplicate groups, split-overlap counts | Direct / Adapted | Rangaiah et al. 2026; Liu et al. 2024 | Both document duplicate or near-duplicate representations crossing evaluation boundaries. Hash-based tabular grouping is our practical adaptation. |
| Near-duplicate tabular blocking | Adapted / Engineering | Liu et al. 2024; Gerz & Jelali 2026 | The papers motivate near-duplicate risk; normalization, blocking, and thresholds are engineering choices. |
| Group-column audit and group-aware split | Direct | Rangaiah et al. 2026; Saraswat 2026; Tampu et al. 2022; Rosenblatt et al. 2024 | Related subjects/campaigns/volumes can make random rows non-independent. Users declare group semantics. |
| Time-column audit and chronological split | Direct / Adapted | Bernett et al. 2024; Korkmaz 2026; Apicella et al. 2025 | Temporal dependence and inference timing matter; generic date parsing is an implementation adaptation. |
| Pipeline/preprocessing audit | Direct / Engineering | Vrba et al. 2026; Draoui et al. 2026; Korkmaz 2026; Disoki & Sonbol | Transformations and selection must be estimated within training folds. sklearn static inspection is an engineering choice. |
| Feature-selection warning | Direct | Rosenblatt et al. 2024; Disoki & Sonbol | Global supervised selection materially altered case-study estimates. |
| Augmentation/resampling warning | Direct / Adapted | Gerz & Jelali 2026; Draoui et al. 2026 | Split before augmentation/resampling; supported pipeline-pattern recognition is an adaptation. |
| Suspicious proxy/target feature analysis | Direct / Adapted | Bernett et al. 2024; Nazari & Ahmadi 2026; Briere et al. 2025 | Illegitimate/circular features require context. Association, names, and single-feature models create only heuristic evidence. |
| Configurable permutation / negative controls | Adapted | Tampu et al. 2022; Briere et al. 2025 | These works use random labels/permutation questions; small configurable tabular controls are adapted, not a validation guarantee. |
| Original versus safer performance and inflation | Direct / Extension | Rangaiah et al. 2026; Saraswat 2026; Rosenblatt et al. 2024; Hughes & Zhang 2026 | Compare protocols to quantify case-specific differences. Metric formulas and UI are project extensions. |
| Multi-signal risk score and finding schema | Extension | Rosenblatt et al. 2024; Korkmaz 2026; Apicella et al. 2025 | Literature shows heterogeneous effects and workflow-oriented audits; no supplied paper validates this project's 0-100 score. |
| Lightweight notebook/script code audit | Adapted / Engineering | Draoui et al. 2026; Disoki & Sonbol | Code-level manifestations motivate warnings. Regex/AST rules cannot infer arbitrary Python intent. |
| Reproducible report with configuration | Direct / Engineering | Korkmaz 2026; Gerz & Jelali 2026 | Reproducibility and diagnostic output are directly motivated; artifact format is an engineering choice. |
