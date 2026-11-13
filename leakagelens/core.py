from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .detectors import exact_duplicates, feature_row_hashes, group_overlap, near_duplicates, pipeline_audit, suspicious_features, temporal_audit
from .evaluation import comparison_metadata, evaluate, inflation, make_split
from .ingestion import INFERENCE_CONTEXTS, SPLIT_STRATEGIES, TASKS, load_table, profile, validate_frame
from .scoring import aggregate
from .schemas import AuditResult

__version__ = "0.1.0"


@dataclass
class AuditConfig:
    target: str
    task: str = "classification"
    group_column: str | None = None
    time_column: str | None = None
    inference_context: str = "iid"  # iid or temporal
    seed: int = 42
    original_strategy: str = "random"
    run_evaluation: bool = True

    def validate(self, frame: pd.DataFrame | None = None) -> None:
        if self.task not in TASKS:
            raise ValueError(f"Unsupported task '{self.task}'. Use one of {sorted(TASKS)}.")
        if self.inference_context not in INFERENCE_CONTEXTS:
            raise ValueError(f"Unsupported inference_context '{self.inference_context}'. Use one of {sorted(INFERENCE_CONTEXTS)}.")
        if self.original_strategy not in SPLIT_STRATEGIES:
            raise ValueError(f"Unsupported split strategy '{self.original_strategy}'. Use one of {sorted(SPLIT_STRATEGIES)}.")
        if not self.target:
            raise ValueError("A target column is required.")
        if frame is not None:
            for label, column in (("group_column", self.group_column), ("time_column", self.time_column)):
                if column and column not in frame:
                    raise ValueError(f"{label} '{column}' was not found.")
                if column and column == self.target:
                    raise ValueError(f"{label} '{column}' must differ from the target column.")
        if self.time_column and self.inference_context == "temporal" and self.time_column == self.target:
            raise ValueError("The time column must differ from the target column.")


class LeakageLens:
    def __init__(self, config: AuditConfig, pipeline: object | None = None):
        self.config, self.pipeline = config, pipeline
        config.validate()

    def audit_file(self, path: str | Path) -> AuditResult:
        return self.audit(load_table(path))

    def audit(self, frame: pd.DataFrame) -> AuditResult:
        c = self.config
        c.validate(frame)
        validate_frame(frame, c.target, c.task)
        original_train, original_test = make_split(frame, c.target, c.task, c.seed, c.group_column, c.time_column, c.original_strategy)
        findings = []
        findings += exact_duplicates(frame, c.target, original_train, original_test)
        findings += near_duplicates(frame, c.target)
        findings += group_overlap(frame, c.group_column, original_train, original_test)
        findings += temporal_audit(frame, c.time_column, original_train, original_test, c.inference_context)
        findings += suspicious_features(frame, c.target, c.task)
        findings += pipeline_audit(self.pipeline)
        score, level, signals = aggregate(findings)

        original = safer = delta = comparison = None
        if c.run_evaluation:
            original = evaluate(frame, c.target, c.task, self.pipeline, original_train, original_test, c.seed, c.original_strategy, c.group_column, c.time_column)
            hashes = feature_row_hashes(frame.drop(columns=[c.target], errors="ignore"))
            has_duplicate_groups = bool(hashes.duplicated(keep=False).any())
            if c.inference_context == "temporal" and c.time_column:
                safe_strategy = "chronological"
            elif c.group_column or has_duplicate_groups:
                safe_strategy = "group"
            else:
                safe_strategy = c.original_strategy
            safe_groups = frame[c.group_column] if c.group_column else hashes if has_duplicate_groups else None
            safe_label = "duplicate_group" if has_duplicate_groups and not c.group_column else safe_strategy
            safe_train, safe_test = make_split(frame, c.target, c.task, c.seed, c.group_column, c.time_column, safe_strategy, safe_groups)
            safer = evaluate(frame, c.target, c.task, self.pipeline, safe_train, safe_test, c.seed, safe_label, c.group_column, c.time_column)
            delta = inflation(original, safer, c.task)
            comparison = comparison_metadata(original, safer)

        reproducibility = {
            "leakagelens_version": __version__, "seed": c.seed, "task": c.task, "target": c.target,
            "original_strategy": c.original_strategy, "inference_context": c.inference_context,
            "group_column": c.group_column, "time_column": c.time_column,
            "dataset_rows": int(len(frame)), "dataset_columns": int(len(frame.columns)),
            "near_duplicate_max_rows": 100_000,
            "near_duplicate_scope": "rounded/normalized row equality candidates, not general similarity search",
            "pipeline": type(self.pipeline).__name__ if self.pipeline is not None else "default_pipeline",
        }
        return AuditResult(profile(frame, c.target), findings, score, level, signals, original, safer, delta, reproducibility, comparison or {})
