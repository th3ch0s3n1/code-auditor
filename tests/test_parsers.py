"""Tests for all parsers using realistic tool output samples."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from auditor.parsers.ruff_parser import RuffParser
from auditor.parsers.bandit_parser import BanditParser
from auditor.parsers.semgrep_parser import SemgrepParser
from auditor.parsers.eslint_parser import ESLintParser
from auditor.parsers.npm_audit_parser import NpmAuditParser


# ── Ruff ──────────────────────────────────────────────────────────────────────


RUFF_OUTPUT = json.dumps([
    {
        "code": "S307",
        "message": "Use of possibly insecure function - consider using safer alternatives",
        "filename": "/project/views.py",
        "location": {"row": 42, "column": 12},
        "end_location": {"row": 42, "column": 16},
        "fix": None,
        "url": "https://docs.astral.sh/ruff/rules/suspicious-eval-usage",
    }
])


def test_ruff_parser_basic():
    findings = RuffParser().parse(RUFF_OUTPUT, base_path=Path("/project"))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "S307"
    assert f.line == 42
    assert f.tool == "ruff"
    assert f.engine == "python"
    assert "views.py" in f.file


def test_ruff_parser_empty():
    assert RuffParser().parse("") == []
    assert RuffParser().parse("[]") == []


def test_ruff_parser_invalid_json():
    assert RuffParser().parse("not json") == []


# ── Bandit ────────────────────────────────────────────────────────────────────


BANDIT_OUTPUT = json.dumps({
    "results": [
        {
            "filename": "/project/views.py",
            "test_id": "B307",
            "test_name": "eval",
            "issue_text": "Use of eval detected.",
            "issue_severity": "HIGH",
            "issue_confidence": "HIGH",
            "line_number": 15,
            "code": "eval(expr)",
        }
    ],
    "errors": [],
    "metrics": {},
})


def test_bandit_parser_basic():
    findings = BanditParser().parse(BANDIT_OUTPUT, base_path=Path("/project"))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "B307"
    assert f.raw_severity == "HIGH"
    assert f.tool == "bandit"
    assert f.code_snippet == "eval(expr)"


def test_bandit_parser_empty():
    assert BanditParser().parse("") == []


# ── Semgrep ───────────────────────────────────────────────────────────────────


SEMGREP_OUTPUT = json.dumps({
    "results": [
        {
            "check_id": "python.django.security.injection.sql.sql-injection",
            "path": "/project/views.py",
            "start": {"line": 10, "col": 5},
            "end": {"line": 10, "col": 60},
            "extra": {
                "message": "SQL injection detected.",
                "severity": "ERROR",
                "metadata": {"category": "security", "cwe": "CWE-89"},
                "lines": 'cursor.execute("SELECT * FROM ... %s" % user_id)',
            },
        }
    ],
    "errors": [],
})


def test_semgrep_parser_basic():
    findings = SemgrepParser().parse(SEMGREP_OUTPUT, base_path=Path("/project"))
    assert len(findings) == 1
    f = findings[0]
    assert f.raw_severity == "ERROR"
    assert f.tool == "semgrep"
    assert f.engine == "django"
    assert f.extra["metadata"]["category"] == "security"


# ── ESLint ────────────────────────────────────────────────────────────────────


ESLINT_OUTPUT = json.dumps([
    {
        "filePath": "/project/src/App.jsx",
        "messages": [
            {
                "ruleId": "no-eval",
                "severity": 2,
                "message": "eval can be harmful.",
                "line": 12,
                "column": 5,
                "source": "eval(expr)",
            },
            {
                "ruleId": "react/no-danger",
                "severity": 2,
                "message": 'Dangerous target="_blank" usage.',
                "line": 20,
                "column": 3,
            },
        ],
        "errorCount": 2,
        "warningCount": 0,
    }
])


def test_eslint_parser_basic():
    findings = ESLintParser().parse(ESLINT_OUTPUT, base_path=Path("/project"))
    assert len(findings) == 2
    assert findings[0].rule_id == "no-eval"
    assert findings[0].raw_severity == "2"
    assert findings[0].tool == "eslint"


# ── npm audit ─────────────────────────────────────────────────────────────────


NPM_AUDIT_OUTPUT = json.dumps({
    "auditReportVersion": 2,
    "vulnerabilities": {
        "lodash": {
            "name": "lodash",
            "severity": "high",
            "isDirect": True,
            "via": [{"source": 1067, "title": "Prototype Pollution", "url": "https://github.com/advisories/GHSA-1"}],
            "range": "<4.17.21",
            "nodes": ["node_modules/lodash"],
            "fixAvailable": {"name": "lodash", "version": "4.17.21"},
        }
    },
    "metadata": {"vulnerabilities": {"critical": 0, "high": 1, "moderate": 0, "low": 0, "info": 0, "total": 1}},
})


def test_npm_audit_parser_basic():
    findings = NpmAuditParser().parse(NPM_AUDIT_OUTPUT)
    assert len(findings) == 1
    f = findings[0]
    assert f.raw_severity == "high"
    assert f.tool == "npm-audit"
    assert "lodash" in f.file
    assert f.extra.get("suggestion") is not None
