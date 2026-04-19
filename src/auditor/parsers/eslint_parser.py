"""ESLint JSON output parser.

ESLint --format json emits an array of file results:

    [
      {
        "filePath": "/abs/path/to/file.jsx",
        "messages": [
          {
            "ruleId": "no-eval",
            "severity": 2,
            "message": "eval can be harmful.",
            "line": 10,
            "column": 5
          }
        ]
      }
    ]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core.raw import RawFinding

logger = logging.getLogger(__name__)


class ESLintParser:
    def parse(self, stdout: str, base_path: Path | None = None) -> list[RawFinding]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.debug("ESLint JSON parse error: %s", exc)
            return []

        findings: list[RawFinding] = []
        for file_result in data:
            try:
                file = file_result.get("filePath", "")
                if base_path and file.startswith(str(base_path)):
                    file = file[len(str(base_path)):].lstrip("/\\")

                for msg in file_result.get("messages", []):
                    severity = msg.get("severity", 1)
                    if severity == 0:
                        continue  # off — skip
                    findings.append(RawFinding(
                        file=file,
                        rule_id=msg.get("ruleId") or "eslint.unknown",
                        message=msg.get("message", ""),
                        tool="eslint",
                        engine="react",
                        raw_severity=str(severity),
                        line=msg.get("line"),
                        col=msg.get("column"),
                        code_snippet=msg.get("source"),
                    ))
            except Exception as exc:
                logger.debug("ESLint file parse error: %s", exc)

        return findings
