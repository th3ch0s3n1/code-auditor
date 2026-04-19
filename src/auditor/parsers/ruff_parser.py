"""Ruff JSON output parser.

Ruff --output-format json emits an array of objects:

    [{"code": "E501", "message": "...", "filename": "...",
      "location": {"row": 1, "column": 1}, ...}]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core.raw import RawFinding

logger = logging.getLogger(__name__)


class RuffParser:
    def parse(self, stdout: str, base_path: Path | None = None) -> list[RawFinding]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.debug("Ruff JSON parse error: %s", exc)
            return []

        findings: list[RawFinding] = []
        for item in data:
            try:
                file = item.get("filename", "")
                if base_path and file.startswith(str(base_path)):
                    file = file[len(str(base_path)):].lstrip("/\\")

                loc = item.get("location", {})
                findings.append(RawFinding(
                    file=file,
                    rule_id=item.get("code", "UNKNOWN"),
                    message=item.get("message", ""),
                    tool="ruff",
                    engine="python",
                    raw_severity=item.get("code", "E")[0],  # first letter is severity hint
                    line=loc.get("row"),
                    col=loc.get("column"),
                    extra={"url": item.get("url")},
                ))
            except Exception as exc:
                logger.debug("Ruff item parse error: %s", exc)
        return findings
