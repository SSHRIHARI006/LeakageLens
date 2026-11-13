"""End-to-end audit workflow tests (spec 6.1)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from leakagelens import AuditConfig, LeakageLens


def test_audit_returns_complete_result(clean_frame):
    result = LeakageLens(AuditConfig(target="target", seed=5)).audit(clean_frame)
    assert result.dataset_summary["rows"] == len(clean_frame)
    assert 0 <= result.risk_score <= 100
    assert result.risk_level in {"LOW", "MODERATE", "HIGH", "CRITICAL"}
    assert result.original_evaluation is not None and result.safer_evaluation is not None
    assert result.reproducibility["seed"] == 5
    assert result.reproducibility["dataset_rows"] == len(clean_frame)
    assert set(result.signal_scores) == set(result.signal_scores)  # dict of signals
    json.dumps(result.to_dict())


def test_input_dataframe_is_not_mutated(duplicate_frame):
    before = duplicate_frame.copy(deep=True)
    LeakageLens(AuditConfig(target="target", seed=2)).audit(duplicate_frame)
    pd.testing.assert_frame_equal(before, duplicate_frame)


def test_duplicate_audit_uses_duplicate_group_safer_split(duplicate_frame):
    result = LeakageLens(AuditConfig(target="target", seed=2)).audit(duplicate_frame)
    assert any(f.category == "duplicate" for f in result.findings)
    assert result.safer_evaluation.strategy == "duplicate_group"


def test_group_audit_produces_group_safer_split(group_frame):
    result = LeakageLens(AuditConfig(target="target", group_column="entity", seed=2)).audit(group_frame)
    assert result.original_evaluation.protocol["group_column"] == "entity"
    assert result.safer_evaluation.strategy == "group"


def test_temporal_audit_produces_chronological_safer_split(temporal_frame):
    config = AuditConfig(target="target", time_column="event_date", inference_context="temporal", seed=2)
    result = LeakageLens(config).audit(temporal_frame)
    assert result.safer_evaluation.strategy == "chronological"
    assert result.comparison["evaluation_rows_fixed"] is False


def test_run_evaluation_false_still_reports_findings(duplicate_frame):
    result = LeakageLens(AuditConfig(target="target", run_evaluation=False)).audit(duplicate_frame)
    assert result.original_evaluation is None
    assert result.safer_evaluation is None
    assert result.inflation is None
    assert any(f.category == "duplicate" for f in result.findings)


def test_audit_file_matches_audit(tmp_path, duplicate_frame):
    path = tmp_path / "data.csv"
    duplicate_frame.to_csv(path, index=False)
    by_path = LeakageLens(AuditConfig(target="target", seed=1)).audit_file(path)
    by_frame = LeakageLens(AuditConfig(target="target", seed=1)).audit(pd.read_csv(path))
    assert by_path.to_dict() == by_frame.to_dict()


def test_audit_is_reproducible(clean_frame):
    first = LeakageLens(AuditConfig(target="target", seed=13)).audit(clean_frame).to_dict()
    second = LeakageLens(AuditConfig(target="target", seed=13)).audit(clean_frame).to_dict()
    assert first == second


def test_audit_rejects_invalid_input(clean_frame):
    with pytest.raises(ValueError, match="not found"):
        LeakageLens(AuditConfig(target="absent")).audit(clean_frame)
    single = pd.DataFrame({"x": [1, 2, 3], "target": [0, 0, 0]})
    with pytest.raises(ValueError, match="at least two"):
        LeakageLens(AuditConfig(target="target")).audit(single)


def test_risk_score_aggregates_only_reported_signals(duplicate_frame):
    result = LeakageLens(AuditConfig(target="target", seed=2)).audit(duplicate_frame)
    expected = min(100.0, round(sum(result.signal_scores.values()) * .55, 1))
    assert result.risk_score == expected
