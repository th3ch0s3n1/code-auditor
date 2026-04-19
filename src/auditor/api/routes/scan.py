"""Scan routes — trigger and monitor scans."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..models import ScanRequest, ScanResponse, ScanStatusResponse
from ...core.pipeline import Pipeline
from ...core.schema import ScanResult

router = APIRouter()

# In-memory store (replace with a real store for production use)
_results: dict[str, ScanResult | str] = {}  # scan_id → ScanResult | "running"


@router.post("", response_model=ScanResponse, status_code=202)
async def trigger_scan(request: ScanRequest, background_tasks: BackgroundTasks) -> ScanResponse:
    """Queue a scan and return a scan_id immediately."""
    scan_id = uuid.uuid4().hex[:8]
    _results[scan_id] = "running"
    background_tasks.add_task(_run_scan, scan_id, request)
    return ScanResponse(scan_id=scan_id, status="queued", message="Scan started.")


@router.get("/{scan_id}/status", response_model=ScanStatusResponse)
async def scan_status(scan_id: str) -> ScanStatusResponse:
    val = _results.get(scan_id)
    if val is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if val == "running":
        return ScanStatusResponse(scan_id=scan_id, status="running")
    if isinstance(val, str):
        return ScanStatusResponse(scan_id=scan_id, status="error", error=val)
    return ScanStatusResponse(scan_id=scan_id, status="done")


# ── Background task ───────────────────────────────────────────────────────────

async def _run_scan(scan_id: str, request: ScanRequest) -> None:
    try:
        pipeline = Pipeline(
            python_only=request.python_only,
            frontend_only=request.frontend_only,
        )
        result = await pipeline.run(request.path, scan_id=scan_id)
        _results[scan_id] = result
    except Exception as exc:
        _results[scan_id] = f"error: {exc}"
