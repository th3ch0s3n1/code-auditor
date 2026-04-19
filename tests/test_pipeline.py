"""Integration-style tests for the full pipeline."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from auditor.core.pipeline import Pipeline
from auditor.core.raw import RawFinding
from auditor.core.schema import Severity, Category


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_raw(
    file="views.py",
    rule_id="S301",
    message="Unsafe pickle",
    tool="bandit",
    engine="python",
    raw_severity="HIGH",
    line=10,
) -> RawFinding:
    return RawFinding(
        file=file,
        rule_id=rule_id,
        message=message,
        tool=tool,
        engine=engine,
        raw_severity=raw_severity,
        line=line,
    )


# ── Normalizer ────────────────────────────────────────────────────────────────


def test_normalizer_bandit_severity():
    from auditor.core.normalizer import Normalizer
    norm = Normalizer()
    raw = make_raw(raw_severity="HIGH", tool="bandit")
    issue = norm.normalize(raw)
    assert issue.severity == Severity.HIGH
    assert issue.category == Category.SECURITY


def test_normalizer_ruff_security_prefix():
    from auditor.core.normalizer import Normalizer
    raw = make_raw(tool="ruff", engine="python", rule_id="S307", raw_severity="S")
    issue = Normalizer().normalize(raw)
    assert issue.category == Category.SECURITY
    assert issue.severity == Severity.HIGH


def test_normalizer_eslint_severity_2():
    from auditor.core.normalizer import Normalizer
    raw = make_raw(tool="eslint", engine="react", rule_id="no-eval", raw_severity="2")
    issue = Normalizer().normalize(raw)
    assert issue.severity == Severity.HIGH


def test_normalizer_npm_audit():
    from auditor.core.normalizer import Normalizer
    raw = make_raw(tool="npm-audit", engine="dependency", rule_id="npm:lodash", raw_severity="critical")
    issue = Normalizer().normalize(raw)
    assert issue.severity == Severity.CRITICAL
    assert issue.category == Category.DEPENDENCY


# ── Deduplicator ──────────────────────────────────────────────────────────────


def test_deduplicator_removes_exact_duplicates():
    from auditor.core.deduplicator import Deduplicator
    from auditor.core.normalizer import Normalizer
    norm = Normalizer()
    raw = make_raw()
    issue = norm.normalize(raw)
    result = Deduplicator().deduplicate([issue, issue, issue])
    assert len(result) == 1


def test_deduplicator_keeps_unique():
    from auditor.core.deduplicator import Deduplicator
    from auditor.core.normalizer import Normalizer
    norm = Normalizer()
    a = norm.normalize(make_raw(rule_id="S301", tool="bandit"))
    b = norm.normalize(make_raw(rule_id="E501", tool="ruff", raw_severity="E"))
    result = Deduplicator().deduplicate([a, b])
    assert len(result) == 2


# ── Enricher ─────────────────────────────────────────────────────────────────


def test_enricher_adds_risk_score():
    from auditor.core.enricher import Enricher
    from auditor.core.normalizer import Normalizer
    issue = Normalizer().normalize(make_raw(raw_severity="HIGH", tool="bandit"))
    enriched = Enricher().enrich(issue)
    assert enriched.risk_score > 0
    assert "security" in enriched.tags


def test_enricher_boosts_auth_file():
    from auditor.core.enricher import Enricher
    from auditor.core.normalizer import Normalizer
    raw = make_raw(file="auth/views.py", raw_severity="HIGH", tool="bandit")
    issue = Normalizer().normalize(raw)
    enriched = Enricher().enrich(issue)
    assert "auth-sensitive" in enriched.tags
    # Score should be boosted beyond base
    assert enriched.risk_score >= 70 + 15 + 10  # base + security + auth


def test_enricher_penalises_test_file():
    from auditor.core.enricher import Enricher
    from auditor.core.normalizer import Normalizer
    raw = make_raw(file="tests/test_views.py", raw_severity="LOW", tool="bandit")
    issue = Normalizer().normalize(raw)
    enriched = Enricher().enrich(issue)
    assert "test-file" in enriched.tags


# ── Pipeline (with mocked engines) ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_runs_with_mocked_engines(tmp_path):
    """Pipeline should produce a ScanResult even with mocked engines."""
    # Create minimal Python project marker
    (tmp_path / "requirements.txt").write_text("bandit\n")

    mock_engine = AsyncMock()
    mock_engine.name = "mock-engine"
    mock_engine.is_available.return_value = True
    mock_engine.run.return_value = [make_raw(file=str(tmp_path / "views.py"))]

    pipeline = Pipeline(engines=[mock_engine])
    result = await pipeline.run(tmp_path)

    assert result.scan_id
    assert len(result.issues) == 1
    assert result.summary.total == 1


@pytest.mark.asyncio
async def test_pipeline_handles_engine_exception(tmp_path):
    """A crashing engine should add to errors, not crash the pipeline."""
    (tmp_path / "requirements.txt").write_text("bandit\n")

    mock_engine = AsyncMock()
    mock_engine.name = "failing-engine"
    mock_engine.is_available.return_value = True
    mock_engine.run.side_effect = RuntimeError("kaboom")

    pipeline = Pipeline(engines=[mock_engine])
    result = await pipeline.run(tmp_path)

    assert any("kaboom" in e for e in result.errors)
    assert result.summary.total == 0


@pytest.mark.asyncio
async def test_pipeline_no_engines_returns_error(tmp_path):
    result = await Pipeline(engines=[]).run(tmp_path)
    assert result.errors
