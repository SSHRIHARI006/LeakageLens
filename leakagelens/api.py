from __future__ import annotations
from pathlib import Path
import tempfile
from fastapi import FastAPI, HTTPException, Request
from .core import AuditConfig, LeakageLens

app = FastAPI(title="LeakageLens", version="0.1.0")

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/audit")
async def audit(request: Request, target: str, task: str = "classification", group_column: str | None = None, time_column: str | None = None, inference_context: str = "iid"):
    """Audit raw file bytes; use X-Filename to preserve the CSV/XLSX/Parquet suffix."""
    suffix = Path(request.headers.get("x-filename", "data.csv")).suffix
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(await request.body()); location = handle.name
        result = LeakageLens(AuditConfig(target=target, task=task, group_column=group_column or None, time_column=time_column or None, inference_context=inference_context)).audit_file(location)
        return result.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if 'location' in locals(): Path(location).unlink(missing_ok=True)
