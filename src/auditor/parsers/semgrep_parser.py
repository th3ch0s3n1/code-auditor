"""Semgrep JSON output parser.

Semgrep --json emits:

    {
      "results": [
        {
          "check_id": "python.django.security.injection.sql...",
          "path": "views.py",
          "start": {"line": 10, "col": 1},
          "end": {"line": 10, "col": 50},
          "extra": {
            "message": "...",
            "severity": "ERROR",
            "metadata": {"category": "security", "cwe": "CWE-89"},
            "lines": "cursor.execute(...)"
          }
        }
      ],
      "errors": [...]
    }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core.raw import RawFinding

logger = logging.getLogger(__name__)


class SemgrepParser:
    def parse(self, stdout: str, base_path: Path | None = None) -> list[RawFinding]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.debug("Semgrep JSON parse error: %s", exc)
            return []

        findings: list[RawFinding] = []
        for item in data.get("results", []):
            try:
                file = item.get("path", "")
                if base_path and file.startswith(str(base_path)):
                    file = file[len(str(base_path)):].lstrip("/\\")

                extra = item.get("extra", {})
                metadata = extra.get("metadata", {})

                # Extract suggestion from fix / autofix metadata
                suggestion = (
                    metadata.get("fix")
                    or metadata.get("message")
                    or extra.get("fix")
                )

                start = item.get("start", {})
                findings.append(RawFinding(
                    file=file,
                    rule_id=item.get("check_id", "semgrep.unknown"),
                    message=extra.get("message", ""),
                    tool="semgrep",
                    engine="django",
                    raw_severity=extra.get("severity", "WARNING"),
                    line=start.get("line"),
                    col=start.get("col"),
                    code_snippet=extra.get("lines"),
                    extra={
                        "metadata": metadata,
                        "suggestion": suggestion,
                        "tags": metadata.get("tags", []),
                    },
                ))
            except Exception as exc:
                logger.debug("Semgrep item parse error: %s", exc)

        return findings
