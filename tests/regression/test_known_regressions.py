"""Regression tests for previously observed defects (spec 14)."""
from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_every_python_source_file_parses():
    """A syntax error once shipped in the Streamlit app and blocked all verification."""
    for path in list((ROOT / "leakagelens").glob("*.py")) + [ROOT / "ui" / "streamlit_app.py"]:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_streamlit_app_imports_audit_api_not_removed_names():
    source = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    assert "LeakageLens" in source and "AuditConfig" in source
    assert "run_everything" not in source


def test_missing_target_raises_actionable_value_error(clean_frame):
    from leakagelens import AuditConfig, LeakageLens

    with pytest.raises(ValueError, match="target column"):
        LeakageLens(AuditConfig(target="missing")).audit(clean_frame)
    with pytest.raises(ValueError):
        # Must not surface as a KeyError from pandas.
        try:
            LeakageLens(AuditConfig(target="missing")).audit(clean_frame)
        except KeyError as exc:  # pragma: no cover
            pytest.fail(f"raw KeyError leaked: {exc}")


def test_string_binary_labels_do_not_break_metrics():
    from leakagelens.evaluation import _metrics_by_task

    metrics, note = _metrics_by_task(pd.Series(["yes", "no", "yes"]), pd.Series(["yes", "yes", "no"]), "classification")
    assert 0 <= metrics["f1"] <= 1
    assert "yes" in note


def test_missing_sentinel_string_does_not_collide_with_null():
    from leakagelens.detectors import feature_row_hashes

    frame = pd.DataFrame({"a": ["<MISSING>", None]})
    assert feature_row_hashes(frame).nunique() == 2


def test_group_overlap_finding_identifies_shared_entity_count():
    from leakagelens.detectors import group_overlap

    frame = pd.DataFrame({"entity": [1, 2, 1, 2], "target": [0, 1, 1, 0]})
    finding = group_overlap(frame, "entity", [0, 1], [2, 3])[0]
    assert finding.evidence["shared_groups"] == 2
    assert finding.affected_rows == 2


def test_risk_score_cannot_exceed_100(duplicate_frame):
    from leakagelens import AuditConfig, LeakageLens

    result = LeakageLens(AuditConfig(target="target", seed=1)).audit(duplicate_frame)
    assert result.risk_score <= 100


def test_near_duplicate_wording_is_not_overclaimed():
    from leakagelens.detectors import near_duplicates

    frame = pd.DataFrame({"x": [1.0, 1.0], "target": [0, 1]})
    finding = near_duplicates(frame, "target")[0]
    assert "candidate" in finding.title.lower()
    assert finding.verification_status == "heuristic"


def test_readme_promises_are_grounded_in_code():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    for artifact in ("tests/", "validation/", "docs/testing_strategy.md"):
        assert artifact.lower() in readme
