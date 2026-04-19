"""API request / response models."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    path: str = Field(..., description="Absolute path of the directory to scan.")
    python_only: bool = False
    frontend_only: bool = False
    fail_on: Optional[str] = None


class ScanResponse(BaseModel):
    scan_id: str
    status: str = "queued"
    message: str = ""


class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str              # queued | running | done | error
    progress: Optional[str] = None
    error: Optional[str] = None
