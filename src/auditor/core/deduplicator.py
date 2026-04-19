"""Deduplicator — removes exact duplicates and groups semantic near-duplicates."""

from __future__ import annotations

import logging

from .schema import Issue, SEVERITY_ORDER

logger = logging.getLogger(__name__)

# Lines within this distance are considered the same location for semantic dedup
_LINE_WINDOW = 3


class Deduplicator:
    """Two-pass deduplication: exact hash, then semantic (same location, different tool)."""

    def deduplicate(self, issues: list[Issue]) -> list[Issue]:
        # Pass 1 — exact ID dedup
        seen: set[str] = set()
        unique: list[Issue] = []
        for issue in issues:
            if issue.id not in seen:
                seen.add(issue.id)
                unique.append(issue)

        initial_count = len(issues)
        after_exact = len(unique)
        logger.debug(
            "Exact dedup: %d → %d (removed %d)", initial_count, after_exact, initial_count - after_exact
        )

        # Pass 2 — semantic dedup across tools
        result = self._semantic_dedup(unique)
        logger.debug(
            "Semantic dedup: %d → %d (removed %d)", after_exact, len(result), after_exact - len(result)
        )
        return result

    # ── Semantic deduplication ────────────────────────────────────────────────

    def _semantic_dedup(self, issues: list[Issue]) -> list[Issue]:
        """
        Group issues that refer to the same location (file + line ±3) in the same
        category but from different tools.  Keep only the highest-severity representative.
        """
        skip: set[str] = set()
        result: list[Issue] = []

        for i, issue in enumerate(issues):
            if issue.id in skip:
                continue

            # Find cross-tool duplicates at the same location
            group: list[Issue] = []
            for j, other in enumerate(issues):
                if i == j or other.id in skip:
                    continue
                if (
                    issue.file == other.file
                    and issue.category == other.category
                    and issue.tool != other.tool
                    and issue.line is not None
                    and other.line is not None
                    and abs(issue.line - other.line) <= _LINE_WINDOW
                ):
                    group.append(other)
                    skip.add(other.id)

            if group:
                all_in_group = [issue] + group
                best = max(all_in_group, key=lambda x: SEVERITY_ORDER[x.severity])
                result.append(best)
            else:
                result.append(issue)

        return result
