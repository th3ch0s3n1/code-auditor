"""Pipeline — orchestrates detection, parallel engine execution, and post-processing."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import Counter
from pathlib import Path

from .deduplicator import Deduplicator
from .detector import ProjectDetector, ProjectInfo
from .enricher import Enricher
from .normalizer import Normalizer
from .schema import SEVERITY_ORDER, ScanResult, ScanSummary, Severity

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Usage::

        result = await Pipeline().run("/path/to/project")
    """

    def __init__(
        self,
        engines=None,           # explicit engine list; None = auto-detect
        use_cache: bool = True,
        since_commit: str | None = None,
        python_only: bool = False,
        frontend_only: bool = False,
    ):
        self._explicit_engines = engines or []
        self.use_cache = use_cache
        self.since_commit = since_commit
        self.python_only = python_only
        self.frontend_only = frontend_only
        self._normalizer = Normalizer()
        self._deduplicator = Deduplicator()
        self._enricher = Enricher()

    # ── Main entry point ──────────────────────────────────────────────────────

    async def run(self, path: str | Path, scan_id: str | None = None) -> ScanResult:
        scan_id = scan_id or uuid.uuid4().hex[:8]
        target = Path(path).resolve()
        t0 = time.monotonic()

        # Detect project types
        info = ProjectDetector().detect(target)

        # Optionally filter by commit diff
        changed_files: set[str] | None = None
        if self.since_commit:
            changed_files = await self._git_changed_files(target, self.since_commit)
            logger.info("Incremental scan: %d changed files", len(changed_files or []))

        result = ScanResult(
            scan_id=scan_id,
            target_path=str(target),
            project_types=info.project_types,
        )

        # Select engines
        engines = self._select_engines(info)
        if not engines:
            result.errors.append("No engines matched the detected project types.")
            return result

        logger.info("Running %d engines on %s", len(engines), target)

        # Run all engines in parallel
        tasks = [e.run(target) for e in engines]
        engine_results = await asyncio.gather(*tasks, return_exceptions=True)

        raw_findings = []
        for engine, res in zip(engines, engine_results):
            if isinstance(res, BaseException):
                msg = f"{engine.name}: {type(res).__name__}: {res}"
                logger.error(msg)
                result.errors.append(msg)
            else:
                # Optionally filter to changed files only
                if changed_files is not None:
                    res = [f for f in res if f.file in changed_files]
                raw_findings.extend(res)
                logger.debug("%s produced %d findings", engine.name, len(res))

        # Normalize → deduplicate → enrich
        issues = [self._normalizer.normalize(f) for f in raw_findings]
        pre_dedup = len(issues)
        issues = self._deduplicator.deduplicate(issues)
        issues = [self._enricher.enrich(i) for i in issues]

        # Sort: severity desc → file → line
        issues.sort(key=lambda x: (-SEVERITY_ORDER[x.severity], x.file, x.line or 0))

        result.issues = issues
        result.summary = _build_summary(
            issues,
            duplicates_removed=pre_dedup - len(issues),
            duration=time.monotonic() - t0,
        )
        return result

    # ── Engine selection ──────────────────────────────────────────────────────

    def _select_engines(self, info: ProjectInfo):
        if self._explicit_engines:
            return self._explicit_engines

        from ..engines.python.ruff import RuffEngine
        from ..engines.python.bandit import BanditEngine
        from ..engines.django.semgrep import SemgrepEngine
        from ..engines.react.eslint import ESLintEngine
        from ..engines.react.npm_audit import NpmAuditEngine

        candidates = []

        if not self.frontend_only:
            if info.has_python:
                candidates += [RuffEngine(), BanditEngine()]
            if info.has_django:
                candidates += [SemgrepEngine()]

        if not self.python_only:
            if info.has_react:
                candidates += [
                    ESLintEngine(react_root=info.react_root),
                    NpmAuditEngine(react_root=info.react_root),
                ]

        # Filter to tools that are actually installed
        available = [e for e in candidates if e.is_available()]
        skipped = [e.name for e in candidates if not e.is_available()]
        if skipped:
            logger.warning("Skipping unavailable tools: %s", ", ".join(skipped))

        return available

    # ── Git diff helper ───────────────────────────────────────────────────────

    @staticmethod
    async def _git_changed_files(cwd: Path, since: str) -> set[str] | None:
        from .runner import AsyncRunner
        result = await AsyncRunner().run(
            ["git", "diff", "--name-only", since],
            cwd=str(cwd),
            timeout=30,
        )
        if not result.ok or result.not_found:
            logger.warning("git diff failed: %s", result.stderr)
            return None
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}


# ── Summary builder ───────────────────────────────────────────────────────────


def _build_summary(issues, duplicates_removed: int, duration: float) -> ScanSummary:
    counts = Counter(i.severity for i in issues)
    by_cat = Counter(i.category.value for i in issues)
    by_tool = Counter(i.tool for i in issues)
    files = {i.file for i in issues}
    return ScanSummary(
        total=len(issues),
        critical=counts.get(Severity.CRITICAL, 0),
        high=counts.get(Severity.HIGH, 0),
        medium=counts.get(Severity.MEDIUM, 0),
        low=counts.get(Severity.LOW, 0),
        info=counts.get(Severity.INFO, 0),
        duplicates_removed=duplicates_removed,
        by_category=dict(by_cat),
        by_tool=dict(by_tool),
        files_scanned=len(files),
        duration_seconds=round(duration, 2),
    )
