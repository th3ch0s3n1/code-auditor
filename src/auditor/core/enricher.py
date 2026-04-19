"""Enricher — adds risk scores, tags, and fix suggestions to normalised issues."""

from __future__ import annotations

from .schema import Category, Issue, Severity

# Risk score baseline per severity
_BASE_SCORES: dict[Severity, int] = {
    Severity.CRITICAL: 90,
    Severity.HIGH: 70,
    Severity.MEDIUM: 40,
    Severity.LOW: 15,
    Severity.INFO: 5,
}

# Path substrings that boost risk (auth / secrets-related files)
_AUTH_KEYWORDS = frozenset({
    "auth", "login", "logout", "token", "password", "secret", "key",
    "credential", "jwt", "session", "oauth", "permission",
})

# Path prefixes that indicate test files (reduce risk)
_TEST_PREFIXES = ("test_", "tests/", "spec/", "__tests__/", "test/")


class Enricher:
    """Compute risk_score, tags, and suggestion for each Issue."""

    def enrich(self, issue: Issue) -> Issue:
        score = _BASE_SCORES[issue.severity]
        tags = list(issue.tags)
        suggestion = issue.suggestion

        # Security boost
        if issue.category == Category.SECURITY:
            score = min(100, score + 15)
            _add_tag(tags, "security")

        # Dependency vulnerabilities
        if issue.category == Category.DEPENDENCY:
            _add_tag(tags, "dependency")

        # Performance tag
        if issue.category == Category.PERFORMANCE:
            _add_tag(tags, "performance")

        # Auth-sensitive file boost
        file_lower = issue.file.lower()
        if any(kw in file_lower for kw in _AUTH_KEYWORDS):
            score = min(100, score + 10)
            _add_tag(tags, "auth-sensitive")

        # Test file penalty
        if _is_test_file(issue.file):
            score = max(0, score - 10)
            _add_tag(tags, "test-file")

        # Suggestion
        if not suggestion:
            suggestion = _suggest(issue)

        return issue.model_copy(update={
            "risk_score": score,
            "tags": tags,
            "suggestion": suggestion,
        })


# ── Helpers ───────────────────────────────────────────────────────────────────


def _add_tag(tags: list[str], tag: str) -> None:
    if tag not in tags:
        tags.append(tag)


def _is_test_file(path: str) -> bool:
    lower = path.lower().replace("\\", "/")
    return any(lower.startswith(p) or f"/{p}" in lower for p in _TEST_PREFIXES)


def _suggest(issue: Issue) -> str | None:
    rule = issue.rule_id.lower()
    msg = issue.message.lower()

    if "sql" in rule or "sql-inject" in msg or "b608" in rule:
        return "Use parameterised queries or an ORM; never interpolate user input into SQL."
    if "csrf" in rule or "csrf" in msg:
        return "Protect the view with CsrfViewMiddleware or @csrf_protect."
    if "dangerouslysetinnerhtml" in msg or "xss" in rule:
        return "Sanitise with DOMPurify before rendering HTML."
    if "select_related" in rule or "n+1" in msg or "n_plus_1" in rule:
        return "Add .select_related() or .prefetch_related() to eliminate N+1 queries."
    if "debug" in rule and "true" in msg:
        return "Set DEBUG=False in production; load it from an environment variable."
    if "secret" in rule or "hardcoded" in msg:
        return "Move secrets to environment variables; use python-decouple or similar."
    if "eval" in rule or "eval(" in msg:
        return "Avoid eval(); use ast.literal_eval() for safe expression parsing."
    if "pickle" in rule or "pickle" in msg:
        return "Do not unpickle untrusted data; use JSON or MessagePack instead."
    if "subprocess" in rule or "shell=true" in msg:
        return "Avoid shell=True; pass a list of arguments to subprocess functions."
    if "b101" in rule:
        return "Remove assert statements from production code; raise explicit exceptions."
    return None
