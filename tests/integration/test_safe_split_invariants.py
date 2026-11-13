"""Invariants that LeakageLens' safer evaluations must always satisfy (spec 6.2)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from leakagelens import AuditConfig, LeakageLens
from leakagelens.detectors import feature_row_hashes
from leakagelens.evaluation import make_split


def test_duplicate_audit_safer_split_has_no_cross_split_hashes(duplicate_frame):
    result = LeakageLens(AuditConfig(target="target", seed=4)).audit(duplicate_frame)
    hashes = feature_row_hashes(duplicate_frame.drop(columns=["target"]))
    safe_train, safe_test = make_split(
        duplicate_frame, "target", "classification", 4, None, None, "group", hashes
    )
    assert set(hashes.iloc[safe_train]).isdisjoint(set(hashes.iloc[safe_test]))
    assert result.safer_evaluation.strategy == "duplicate_group"


def test_duplicate_split_fingerprint_matches_internal_choice(duplicate_frame):
    from leakagelens.evaluation import _fingerprint

    result = LeakageLens(AuditConfig(target="target", seed=4)).audit(duplicate_frame)
    hashes = feature_row_hashes(duplicate_frame.drop(columns=["target"]))
    _, safe_test = make_split(duplicate_frame, "target", "classification", 4, None, None, "group", hashes)
    assert result.safer_evaluation.protocol["test_index_fingerprint"] == _fingerprint(safe_test)


def test_group_audit_safer_split_is_disjoint(group_frame):
    result = LeakageLens(AuditConfig(target="target", group_column="entity", seed=4)).audit(group_frame)
    train, test = make_split(group_frame, "target", "classification", 4, "entity", None, "group")
    assert set(group_frame["entity"].iloc[train]).isdisjoint(set(group_frame["entity"].iloc[test]))
    assert result.safer_evaluation.strategy == "group"


def test_chronological_audit_safer_split_respects_time_order(temporal_frame):
    config = AuditConfig(target="target", time_column="event_date", inference_context="temporal", seed=4)
    LeakageLens(config).audit(temporal_frame)
    train, test = make_split(temporal_frame, "target", "classification", 4, None, "event_date", "chronological")
    dates = pd.to_datetime(temporal_frame["event_date"])
    assert dates.iloc[train].max() <= dates.iloc[test].min()
    assert len(np.intersect1d(train, test)) == 0


def test_every_row_is_used_exactly_once(clean_frame):
    configs = [
        AuditConfig(target="target", seed=6),
        AuditConfig(target="target", seed=6, original_strategy="group", group_column="segment"),
    ]
    for config in configs:
        result = LeakageLens(config).audit(clean_frame)
        for evaluation in (result.original_evaluation, result.safer_evaluation):
            assert evaluation.train_size + evaluation.test_size == len(clean_frame)
