"""Unified issue schema — every engine output normalises to these types."""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Severity ──────────────────────────────────────────────────────────────────


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}

SEVERITY_COLORS: dict[Severity, str] = {
    Severity.CRITICAL: "bright_red",
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}


# ── Category ──────────────────────────────────────────────────────────────────


class Category(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    MAINTAINABILITY = "maintainability"
    DEPENDENCY = "dependency"


# ── Core issue ────────────────────────────────────────────────────────────────


class Issue(BaseModel):
    id: str
    file: str
    line: Optional[int] = None
    col: Optional[int] = None
    tool: str                  # ruff | bandit | semgrep | eslint | npm-audit
    engine: str                # python | django | react | dependency
    category: Category
    severity: Severity
    rule_id: str
    message: str
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    risk_score: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    duplicate_of: Optional[str] = None

    @staticmethod
    def make_id(tool: str, file: str, line: Optional[int], rule_id: str) -> str:
        raw = f"{tool}:{file}:{line}:{rule_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Summary & result ──────────────────────────────────────────────────────────


class ScanSummary(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    duplicates_removed: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    by_tool: dict[str, int] = Field(default_factory=dict)
    files_scanned: int = 0
    duration_seconds: float = 0.0


class ScanResult(BaseModel):
    scan_id: str
    target_path: str
    issues: list[Issue] = Field(default_factory=list)
    summary: ScanSummary = Field(default_factory=ScanSummary)
    errors: list[str] = Field(default_factory=list)
    project_types: list[str] = Field(default_factory=list)
