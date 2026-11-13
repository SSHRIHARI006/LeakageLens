"""HTTP API tests (spec 7)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from leakagelens.api import app  # noqa: E402

client = TestClient(app)


def csv_bytes(frame) -> bytes:
    return frame.to_csv(index=False).encode()


def post_audit(body: bytes, filename: str = "data.csv", **params):
    query = {"target": "target", **params}
    return client.post("/audit", params=query, content=body, headers={"X-Filename": filename})


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_valid_csv_audit(clean_frame):
    response = post_audit(csv_bytes(clean_frame))
    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_summary"]["rows"] == len(clean_frame)
    assert 0 <= payload["risk_score"] <= 100
    assert "findings" in payload


def test_duplicate_csv_reports_findings(duplicate_frame):
    payload = post_audit(csv_bytes(duplicate_frame)).json()
    assert any(f["category"] == "duplicate" for f in payload["findings"])


def test_regression_task_supported(clean_frame):
    frame = clean_frame.copy()
    frame["target"] = frame["age"] * .1
    response = post_audit(csv_bytes(frame), task="regression")
    assert response.status_code == 200
    assert "rmse" in response.json()["original_evaluation"]["metrics"]


def test_group_and_time_columns(clean_frame, temporal_frame):
    grouped = post_audit(csv_bytes(clean_frame), group_column="segment")
    assert grouped.status_code == 200
    timed = post_audit(
        csv_bytes(temporal_frame), filename="data.csv", time_column="event_date", inference_context="temporal"
    )
    assert timed.status_code == 200


def test_unsupported_suffix_rejected():
    response = post_audit(b"a,b\n1,2\n", filename="data.txt")
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
    assert ".txt" in response.json()["detail"]


def test_empty_body_rejected():
    response = post_audit(b"")
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_invalid_csv_and_missing_target_are_400(clean_frame):
    assert post_audit(b"not,a\ncsv,\n") .status_code == 400
    assert post_audit(csv_bytes(clean_frame), target="absent").status_code == 400


def test_query_enum_validation_is_422(clean_frame):
    assert post_audit(csv_bytes(clean_frame), task="ranking").status_code == 422
    assert post_audit(csv_bytes(clean_frame), inference_context="future").status_code == 422
    assert post_audit(csv_bytes(clean_frame), original_strategy="bogus").status_code == 422


def test_missing_target_parameter_is_422(clean_frame):
    response = client.post("/audit", content=csv_bytes(clean_frame), headers={"X-Filename": "data.csv"})
    assert response.status_code == 422


def test_body_is_treated_as_data_not_a_path(clean_frame):
    payload = f"/etc/passwd\n{clean_frame.to_csv(index=False)}".encode()
    response = post_audit(payload)
    # The first line becomes a header, so the audit fails cleanly rather than reading /etc/passwd.
    assert response.status_code == 400
    assert "/etc/passwd" not in response.json()["detail"]


def test_error_detail_does_not_leak_temp_paths(clean_frame):
    response = post_audit(b"a,a,target\n1,2,0\n")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "/tmp" not in detail and "tmp" not in detail.lower()


def test_temp_files_are_cleaned_up(clean_frame, monkeypatch):
    created: list[str] = []
    real_tempfile = tempfile.NamedTemporaryFile

    def tracking_tempfile(*args, **kwargs):
        handle = real_tempfile(*args, **kwargs)
        created.append(handle.name)
        return handle

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", tracking_tempfile)
    response = post_audit(csv_bytes(clean_frame))
    assert response.status_code == 200
    assert created
    assert all(not Path(name).exists() for name in created)


def test_response_is_json_serializable(duplicate_frame):
    payload = post_audit(csv_bytes(duplicate_frame)).json()
    json.dumps(payload)
    assert "NaN" not in json.dumps(payload)
