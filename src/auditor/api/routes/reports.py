"""Reports routes — retrieve completed scan results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from ...core.schema import ScanResult
from ..routes.scan import _results
from ...reporters import json_reporter, html_reporter

router = APIRouter()


@router.get("", summary="List all completed scan IDs")
async def list_reports() -> list[str]:
    return [k for k, v in _results.items() if isinstance(v, ScanResult)]


@router.get("/{scan_id}", summary="Get full ScanResult as JSON")
async def get_report(scan_id: str) -> ScanResult:
    val = _results.get(scan_id)
    if val is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not isinstance(val, ScanResult):
        raise HTTPException(status_code=409, detail="Scan not completed yet.")
    return val


@router.get("/{scan_id}/html", summary="Get report as HTML page")
async def get_report_html(scan_id: str) -> Response:
    val = _results.get(scan_id)
    if val is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not isinstance(val, ScanResult):
        raise HTTPException(status_code=409, detail="Scan not completed yet.")
    html = html_reporter.render(val)
    return Response(content=html, media_type="text/html")
