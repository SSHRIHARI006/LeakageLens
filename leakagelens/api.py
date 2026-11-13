from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request

from .core import AuditConfig, LeakageLens

app = FastAPI(title="LeakageLens", version="0.1.0")

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls", ".parquet"}


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


def _safe_detail(exc: Exception, location: str | None) -> str:
    """Return an actionable message without leaking local paths or traces."""
    message = "Audit failed. Check the uploaded file and configuration."
    if isinstance(exc, (ValueError, FileNotFoundError)):
        message = str(exc)
    if location:
        message = message.replace(location, "<uploaded>")
    return message


@app.post("/audit")
async def audit(
    request: Request,
    target: str,
    task: Literal["classification", "regression"] = "classification",
    group_column: str | None = None,
    time_column: str | None = None,
    inference_context: Literal["iid", "temporal"] = "iid",
    original_strategy: Literal["random", "group", "chronological"] = "random",
    seed: int = 42,
):
    """Audit raw file bytes; use X-Filename to preserve the CSV/XLSX/Parquet suffix.

    Pipelines are not accepted over HTTP: deserializing arbitrary Python objects
    from an untrusted request is unsafe, so only the default pipeline is evaluated.
    """
    filename = request.headers.get("x-filename", "data.csv")
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}'. Use CSV, XLSX, or Parquet.")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Request body is empty.")
    location: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(body)
            location = handle.name
        result = LeakageLens(AuditConfig(
            target=target, task=task, group_column=group_column or None, time_column=time_column or None,
            inference_context=inference_context, original_strategy=original_strategy, seed=seed,
        )).audit_file(location)
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_safe_detail(exc, location)) from exc
    finally:
        if location:
            Path(location).unlink(missing_ok=True)
