"""Report and JSON serialization tests (spec 5.10)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from leakagelens import AuditConfig, LeakageLens
from leakagelens.reporting import markdown_report, write_report
from leakagelens.schemas import AuditResult, Finding, jsonable


def test_clean_audit_report_contains_required_sections(clean_frame):
    result = LeakageLens(AuditConfig(target="target", seed=1)).audit(clean_frame)
    report = markdown_report(result)
    for heading in ("# LeakageLens audit report", "## Dataset", "## Findings", "## Reproducibility", "## Limitations"):
        assert heading in report
    assert "not a probability" in report


def test_report_without_findings_is_valid():
    result = AuditResult({"rows": 2, "columns": 2}, [], 0.0, "LOW", {})
    report = markdown_report(result)
    assert "No deterministic or heuristic leakage findings were reported." in report


def test_report_handles_unicode_quotes_nested_evidence_and_nulls(tmp_path):
    finding = Finding(
        "test", "duplicate", "high", "high", 80, "Título with \"quotes\" and `code`",
        "Description with ünïcode, | pipes, and newline\ncontent.",
        {"nested": {"items": [1, None, "x"]}, "nan": np.nan, "timestamp": pd.Timestamp("2024-01-01")},
        ["col"], 3, "Recommendation.", "deterministic",
    )
    result = AuditResult({"rows": 5, "columns": 3}, [finding], 44.0, "HIGH", {"duplicate": 80})
    report = markdown_report(result)
    assert "Título" in report
    json.dumps(result.to_dict())  # must not raise
    path = write_report(result, tmp_path / "nested" / "report.md")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == report


def test_to_dict_is_strictly_json_serializable(clean_frame):
    frame = clean_frame.copy()
    frame["when"] = pd.date_range("2024-01-01", periods=len(frame))
    frame["flag"] = [True, False] * (len(frame) // 2)
    result = LeakageLens(AuditConfig(target="target", time_column="when", seed=2)).audit(frame)
    payload = json.dumps(result.to_dict())
    assert "NaN" not in payload
    assert isinstance(json.loads(payload), dict)


def test_jsonable_normalizes_numpy_and_pandas_values():
    value = jsonable({
        "np_int": np.int64(3), "np_float": np.float32(1.5), "np_bool": np.bool_(True),
        "nan": float("nan"), "inf": float("inf"), "series": pd.Series([1, 2]),
        "array": np.array([1.0, np.nan]), "timestamp": pd.Timestamp("2024-01-01"),
    })
    json.dumps(value)
    assert value["np_int"] == 3
    assert value["nan"] is None
    assert value["array"] == [1.0, None]


def test_report_matches_result_values(duplicate_frame):
    result = LeakageLens(AuditConfig(target="target", seed=3)).audit(duplicate_frame)
    report = markdown_report(result)
    assert f"Leakage risk score: **{result.risk_score}/100 ({result.risk_level})**" in report
    for finding in result.findings:
        assert finding.title in report
