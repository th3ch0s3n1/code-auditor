"""Tests for the unified Issue schema."""

from __future__ import annotations

import pytest
from auditor.core.schema import Issue, Category, Severity, ScanResult, ScanSummary


def test_issue_make_id_is_deterministic():
    id1 = Issue.make_id("ruff", "views.py", 10, "E501")
    id2 = Issue.make_id("ruff", "views.py", 10, "E501")
    assert id1 == id2
    assert len(id1) == 16


def test_issue_make_id_differs_on_different_inputs():
    id1 = Issue.make_id("ruff", "views.py", 10, "E501")
    id2 = Issue.make_id("bandit", "views.py", 10, "B101")
    assert id1 != id2


def test_issue_model_roundtrip():
    issue = Issue(
        id="abc123",
        file="app.py",
        line=42,
        tool="ruff",
        engine="python",
        category=Category.SECURITY,
        severity=Severity.HIGH,
        rule_id="S301",
        message="Unsafe pickle",
        risk_score=85,
        tags=["security"],
    )
    data = issue.model_dump()
    restored = Issue.model_validate(data)
    assert restored == issue


def test_scan_summary_defaults():
    s = ScanSummary()
    assert s.total == 0
    assert s.critical == 0
    assert s.by_tool == {}


def test_scan_result_has_empty_issues_by_default():
    r = ScanResult(scan_id="test-1", target_path="/tmp")
    assert r.issues == []
    assert r.errors == []
