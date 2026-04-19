"""Bandit JSON output parser.

Bandit --format json emits:

    {
      "results": [
        {
          "filename": "...",
          "test_id": "B101",
          "test_name": "assert_used",
          "issue_text": "...",
          "issue_severity": "LOW",
          "issue_confidence": "HIGH",
          "line_number": 10,
          "code": "assert something"
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


class BanditParser:
    def parse(self, stdout: str, base_path: Path | None = None) -> list[RawFinding]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.debug("Bandit JSON parse error: %s", exc)
            return []

        findings: list[RawFinding] = []
        for item in data.get("results", []):
            try:
                file = item.get("filename", "")
                if base_path and file.startswith(str(base_path)):
                    file = file[len(str(base_path)):].lstrip("/\\")

                findings.append(RawFinding(
                    file=file,
                    rule_id=item.get("test_id", "B000"),
                    message=item.get("issue_text", ""),
                    tool="bandit",
                    engine="python",
                    raw_severity=item.get("issue_severity", "MEDIUM"),
                    line=item.get("line_number"),
                    col=None,
                    code_snippet=item.get("code"),
                    extra={
                        "confidence": item.get("issue_confidence"),
                        "test_name": item.get("test_name"),
                    },
                ))
            except Exception as exc:
                logger.debug("Bandit item parse error: %s", exc)

        return findings
