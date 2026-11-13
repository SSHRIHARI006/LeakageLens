"""Temporal detector and chronological split tests (spec 5.5)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from leakagelens import AuditConfig, LeakageLens
from leakagelens.detectors import temporal_audit
from leakagelens.evaluation import make_split


def _temporal_frame(dates) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame({"x": np.arange(n, dtype=float), "event_date": dates, "target": np.arange(n) % 2})


def test_valid_chronological_split_has_no_future_finding():
    frame = _temporal_frame(pd.date_range("2024-01-01", periods=40, freq="D"))
    train, test = make_split(frame, "target", "classification", 3, time="event_date", strategy="chronological")
    dates = pd.to_datetime(frame["event_date"])
    assert dates.iloc[train].max() <= dates.iloc[test].min()
    assert temporal_audit(frame, "event_date", train, test, "temporal") == []


def test_future_contaminated_training_split_is_flagged_with_count():
    frame = _temporal_frame(pd.date_range("2024-01-01", periods=40, freq="D"))
    train, test = list(range(10, 40)), list(range(0, 10))
    finding = temporal_audit(frame, "event_date", train, test, "temporal")[0]
    assert finding.title.startswith("Future")
    assert finding.affected_rows == 30
    assert finding.verification_status == "deterministic"


def test_iid_context_ignores_dates():
    frame = _temporal_frame(pd.date_range("2024-01-01", periods=40, freq="D"))
    assert temporal_audit(frame, "event_date", list(range(30)), list(range(30, 40)), "iid") == []


def test_iid_audit_does_not_report_temporal_finding():
    frame = _temporal_frame(pd.date_range("2024-01-01", periods=40, freq="D"))
    result = LeakageLens(AuditConfig(target="target", time_column="event_date", inference_context="iid")).audit(frame)
    assert not any(f.detector_name == "temporal" for f in result.findings)


def test_temporal_audit_requires_context_and_column():
    frame = _temporal_frame(pd.date_range("2024-01-01", periods=10))
    assert temporal_audit(frame, None, [0, 1], [2, 3], "temporal") == []
    with pytest.raises(ValueError, match="not found"):
        temporal_audit(frame, "missing", [0, 1], [2, 3], "temporal")


def test_all_invalid_dates_report_parse_problem():
    frame = _temporal_frame(["not-a-date"] * 10)
    finding = temporal_audit(frame, "event_date", [0, 1, 2], [3, 4, 5], "temporal")[0]
    assert "could not be parsed" in finding.title.lower()
    assert finding.verification_status == "deterministic"


def test_mixed_invalid_dates_warn_and_are_excluded():
    dates = pd.date_range("2024-01-01", periods=9).tolist() + ["oops"]
    frame = _temporal_frame(dates)
    findings = temporal_audit(frame, "event_date", list(range(8)), [8, 9], "temporal")
    invalid = [f for f in findings if "could not be parsed" in f.title.lower()]
    assert invalid and invalid[0].evidence["invalid_rows"] == 1


def test_all_equal_dates_cannot_establish_chronology():
    frame = _temporal_frame([pd.Timestamp("2024-01-01")] * 10)
    findings = temporal_audit(frame, "event_date", [0, 1, 2], [3, 4, 5], "temporal")
    assert any(f.verification_status == "unable_to_determine" for f in findings)


def test_timezone_aware_dates_supported():
    dates = pd.date_range("2024-01-01", periods=20, freq="D", tz="UTC")
    frame = _temporal_frame(dates)
    train, test = make_split(frame, "target", "classification", 5, time="event_date", strategy="chronological")
    assert pd.to_datetime(frame["event_date"].iloc[train]).max() <= pd.to_datetime(frame["event_date"].iloc[test]).min()
    assert temporal_audit(frame, "event_date", train, test, "temporal") == []


def test_chronological_split_sorts_unsorted_input():
    dates = pd.date_range("2024-01-01", periods=20, freq="D")[::-1]  # descending
    frame = _temporal_frame(dates)
    train, test = make_split(frame, "target", "classification", 5, time="event_date", strategy="chronological")
    assert pd.to_datetime(frame["event_date"].iloc[train]).max() <= pd.to_datetime(frame["event_date"].iloc[test]).min()


def test_chronological_split_rejects_unparseable_and_tiny_input():
    frame = _temporal_frame(["bad"] * 10)
    with pytest.raises(ValueError, match="cannot be parsed"):
        make_split(frame, "target", "classification", 1, time="event_date", strategy="chronological")
    tiny = _temporal_frame(pd.date_range("2024-01-01", periods=1))
    with pytest.raises(ValueError, match="too small"):
        make_split(tiny, "target", "classification", 1, time="event_date", strategy="chronological")
    with pytest.raises(ValueError, match="requires a time column"):
        make_split(tiny, "target", "classification", 1, strategy="chronological")


def test_temporal_leakage_audit_end_to_end_uses_safer_chronological_split():
    frame = _temporal_frame(pd.date_range("2024-01-01", periods=40, freq="D"))
    config = AuditConfig(target="target", time_column="event_date", inference_context="temporal", seed=4)
    result = LeakageLens(config).audit(frame)
    assert result.safer_evaluation.strategy == "chronological"
    assert any(f.detector_name == "temporal" for f in result.findings)
