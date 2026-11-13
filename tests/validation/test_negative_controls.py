"""Negative controls: clean families must not produce deterministic findings (spec 9.3)."""
from __future__ import annotations

import pytest

from leakagelens import AuditConfig, LeakageLens
from leakagelens.detectors import exact_duplicates, group_overlap, near_duplicates, suspicious_features, temporal_audit
from validation.generators import generate

CLEAN_FAMILIES = ["SYN-00", "SYN-08", "SYN-09", "SYN-13", "SYN-14", "SYN-15"]


@pytest.mark.parametrize("family", CLEAN_FAMILIES)
def test_clean_family_has_no_deterministic_split_or_duplicate_findings(family):
    frame, manifest = generate(family, 42)
    findings = exact_duplicates(frame, manifest["target"], manifest["train_index"], manifest["test_index"])
    assert not any(f.verification_status == "deterministic" for f in findings)


@pytest.mark.parametrize("family", ["SYN-00", "SYN-08", "SYN-09", "SYN-13"])
def test_clean_family_has_no_near_duplicate_candidates(family):
    frame, manifest = generate(family, 42)
    assert near_duplicates(frame, manifest["target"]) == []


def test_clean_group_family_has_no_group_overlap():
    frame, manifest = generate("SYN-13", 42)
    assert group_overlap(frame, "entity", manifest["train_index"], manifest["test_index"]) == []


def test_iid_date_family_is_not_flagged_temporal():
    frame, manifest = generate("SYN-15", 42)
    assert temporal_audit(frame, "event_date", manifest["train_index"], manifest["test_index"], "iid") == []


def test_chronological_clean_family_is_not_flagged_temporal():
    frame, manifest = generate("SYN-14", 42)
    assert temporal_audit(frame, "event_date", manifest["train_index"], manifest["test_index"], "temporal") == []


def test_legitimate_strong_predictor_is_not_a_name_warning():
    frame, _ = generate("SYN-05", 42)
    findings = suspicious_features(frame, "target", "regression")
    assert not any(f.category == "target_proxy" for f in findings)


def test_clean_full_audit_risk_is_low_and_no_high_findings():
    frame, manifest = generate("SYN-00", 42)
    result = LeakageLens(AuditConfig(target=manifest["target"], seed=42)).audit(frame)
    assert result.risk_level == "LOW"
    assert not [f for f in result.findings if f.severity in {"high", "critical"}]
    assert result.risk_score < 20
