import pandas as pd
from leakagelens import AuditConfig, LeakageLens
from leakagelens.ingestion import validate_frame

def frame():
    return pd.DataFrame({"x": [1, 1, 2, 3, 4, 5, 6, 7], "group": [1,1,2,3,4,5,6,7], "target": [0,0,0,1,0,1,1,1]})

def test_missing_target_rejected():
    try: validate_frame(frame(), "missing")
    except ValueError as exc: assert "not found" in str(exc)
    else: assert False

def test_duplicate_audit_and_evaluation():
    result = LeakageLens(AuditConfig(target="target", group_column="group", seed=5)).audit(frame())
    assert result.original_evaluation is not None
    assert any(f.detector_name == "exact_duplicates" for f in result.findings)
    assert 0 <= result.risk_score <= 100

def test_duplicate_groups_create_safer_split_without_group_column():
    result = LeakageLens(AuditConfig(target="target", seed=5)).audit(frame())
    assert result.safer_evaluation.strategy == "duplicate_group"

def test_temporal_audit():
    data = frame(); data["date"] = pd.date_range("2024-01-01", periods=len(data), freq="D")
    result = LeakageLens(AuditConfig(target="target", time_column="date", inference_context="temporal", seed=4)).audit(data)
    assert result.safer_evaluation.strategy == "chronological"
