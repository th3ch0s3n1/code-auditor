"""Normalizer — converts RawFinding → Issue using a unified mapping."""

from __future__ import annotations

from .raw import RawFinding
from .schema import Category, Issue, Severity


class Normalizer:
    """Map tool-specific findings to the unified Issue schema."""

    # ── Ruff ─────────────────────────────────────────────────────────────────

    _RUFF_CATEGORY: dict[str, Category] = {
        "S": Category.SECURITY,       # flake8-bandit compat
        "B": Category.CORRECTNESS,    # flake8-bugbear
        "E": Category.CORRECTNESS,    # pycodestyle errors
        "F": Category.CORRECTNESS,    # pyflakes
        "W": Category.MAINTAINABILITY,
        "C": Category.MAINTAINABILITY,
        "N": Category.MAINTAINABILITY,
        "UP": Category.MAINTAINABILITY,
        "ANN": Category.MAINTAINABILITY,
        "ARG": Category.MAINTAINABILITY,
        "PL": Category.MAINTAINABILITY,
        "PT": Category.CORRECTNESS,
        "RUF": Category.CORRECTNESS,
    }

    _RUFF_SEVERITY: dict[str, Severity] = {
        "S": Severity.HIGH,
        "E": Severity.MEDIUM,
        "F": Severity.MEDIUM,
        "B": Severity.MEDIUM,
        "W": Severity.LOW,
        "C": Severity.LOW,
        "N": Severity.LOW,
        "UP": Severity.LOW,
        "ANN": Severity.LOW,
        "ARG": Severity.LOW,
        "PL": Severity.LOW,
        "RUF": Severity.LOW,
    }

    # High-severity ruff rules regardless of prefix
    _RUFF_HIGH: frozenset[str] = frozenset({
        "S301", "S302", "S303", "S304", "S305", "S306", "S307",  # deserialization / code exec
        "S324", "S501", "S502", "S503", "S504", "S506",          # crypto / SSL
        "S601", "S602", "S603", "S604", "S605", "S606",          # shell injection
        "S701",                                                    # jinja2 autoescape
    })

    # ── Bandit ────────────────────────────────────────────────────────────────

    _BANDIT_SEVERITY: dict[str, Severity] = {
        "HIGH": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "LOW": Severity.LOW,
    }

    # ── Semgrep ───────────────────────────────────────────────────────────────

    _SEMGREP_SEVERITY: dict[str, Severity] = {
        "ERROR": Severity.HIGH,
        "WARNING": Severity.MEDIUM,
        "INFO": Severity.LOW,
    }

    # ── ESLint ────────────────────────────────────────────────────────────────

    _ESLINT_SEVERITY: dict[int, Severity] = {
        2: Severity.HIGH,
        1: Severity.MEDIUM,
        0: Severity.INFO,
    }

    # ── npm audit ─────────────────────────────────────────────────────────────

    _NPM_SEVERITY: dict[str, Severity] = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "moderate": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }

    # ── Public API ────────────────────────────────────────────────────────────

    def normalize(self, raw: RawFinding) -> Issue:
        category, severity = self._resolve(raw)
        return Issue(
            id=Issue.make_id(raw.tool, raw.file, raw.line, raw.rule_id),
            file=raw.file,
            line=raw.line,
            col=raw.col,
            tool=raw.tool,
            engine=raw.engine,
            category=category,
            severity=severity,
            rule_id=raw.rule_id,
            message=raw.message,
            code_snippet=raw.code_snippet,
            suggestion=raw.extra.get("suggestion"),
            tags=list(raw.extra.get("tags", [])),
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve(self, raw: RawFinding) -> tuple[Category, Severity]:
        match raw.tool:
            case "ruff":
                return self._ruff(raw)
            case "bandit":
                return self._bandit(raw)
            case "semgrep":
                return self._semgrep(raw)
            case "eslint":
                return self._eslint(raw)
            case "npm-audit":
                sev = self._NPM_SEVERITY.get(raw.raw_severity.lower(), Severity.MEDIUM)
                return Category.DEPENDENCY, sev
            case _:
                return Category.CORRECTNESS, Severity.MEDIUM

    def _ruff(self, raw: RawFinding) -> tuple[Category, Severity]:
        rule = raw.rule_id.upper()
        # Extract alphabetic prefix
        prefix = "".join(c for c in rule if c.isalpha())

        category = (
            self._RUFF_CATEGORY.get(prefix[:2])
            or self._RUFF_CATEGORY.get(prefix[:1], Category.CORRECTNESS)
        )
        if rule in self._RUFF_HIGH:
            severity = Severity.HIGH
        else:
            severity = self._RUFF_SEVERITY.get(prefix[:1], Severity.MEDIUM)
        return category, severity

    def _bandit(self, raw: RawFinding) -> tuple[Category, Severity]:
        severity = self._BANDIT_SEVERITY.get(raw.raw_severity.upper(), Severity.MEDIUM)
        return Category.SECURITY, severity

    def _semgrep(self, raw: RawFinding) -> tuple[Category, Severity]:
        severity = self._SEMGREP_SEVERITY.get(raw.raw_severity.upper(), Severity.MEDIUM)
        meta_cat = raw.extra.get("metadata", {}).get("category", "security")
        try:
            category = Category(meta_cat)
        except ValueError:
            category = Category.SECURITY
        return category, severity

    def _eslint(self, raw: RawFinding) -> tuple[Category, Severity]:
        try:
            sev_int = int(raw.raw_severity)
        except (ValueError, TypeError):
            sev_int = 1
        severity = self._ESLINT_SEVERITY.get(sev_int, Severity.MEDIUM)

        rule = raw.rule_id or ""
        if rule.startswith("security/") or "xss" in rule.lower() or "injection" in rule.lower():
            category = Category.SECURITY
        elif "no-eval" in rule or "dangerous" in rule:
            category = Category.SECURITY
        elif rule.startswith("react/"):
            category = Category.CORRECTNESS
        else:
            category = Category.MAINTAINABILITY
        return category, severity
