"""npm audit JSON output parser.

npm audit --json (v7+/audit report v2) emits:

    {
      "auditReportVersion": 2,
      "vulnerabilities": {
        "lodash": {
          "name": "lodash",
          "severity": "high",
          "isDirect": true,
          "via": [...],
          "range": "<4.17.21",
          "fixAvailable": {...}
        }
      },
      "metadata": {"vulnerabilities": {"critical": 0, "high": 1, ...}}
    }

Also handles the older v1 format (results array under "advisories").
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..core.raw import RawFinding

logger = logging.getLogger(__name__)


class NpmAuditParser:
    def parse(self, stdout: str, base_path: Path | None = None) -> list[RawFinding]:
        if not stdout.strip():
            return []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.debug("npm audit JSON parse error: %s", exc)
            return []

        # Audit report v2
        if data.get("auditReportVersion") == 2:
            return self._parse_v2(data)

        # Older v1
        if "advisories" in data:
            return self._parse_v1(data)

        return []

    # ── v2 ────────────────────────────────────────────────────────────────────

    def _parse_v2(self, data: dict) -> list[RawFinding]:
        findings: list[RawFinding] = []
        for pkg_name, vuln in data.get("vulnerabilities", {}).items():
            try:
                severity = vuln.get("severity", "moderate")
                via = vuln.get("via", [])
                # Collect advisory URLs / titles from the "via" chain
                advisories = [v for v in via if isinstance(v, dict)]
                advisory = advisories[0] if advisories else {}

                title = advisory.get("title") or f"Vulnerable dependency: {pkg_name}"
                url = advisory.get("url") or ""
                fix = vuln.get("fixAvailable")
                suggestion = None
                if isinstance(fix, dict):
                    suggestion = f"Upgrade to {fix.get('name')} {fix.get('version')}"
                elif fix is True:
                    suggestion = "Run `npm audit fix` to apply the available fix."

                source = advisory.get("source")
                rule_id = f"npm:{source}" if source is not None else f"npm:{pkg_name}"
                findings.append(RawFinding(
                    file=f"package.json#{pkg_name}",
                    rule_id=rule_id,
                    message=title,
                    tool="npm-audit",
                    engine="dependency",
                    raw_severity=severity,
                    line=None,
                    col=None,
                    extra={
                        "range": vuln.get("range"),
                        "url": url,
                        "suggestion": suggestion,
                        "tags": ["dependency"],
                    },
                ))
            except Exception as exc:
                logger.debug("npm audit v2 item parse error: %s", exc)
        return findings

    # ── v1 ────────────────────────────────────────────────────────────────────

    def _parse_v1(self, data: dict) -> list[RawFinding]:
        findings: list[RawFinding] = []
        for adv_id, adv in data.get("advisories", {}).items():
            try:
                findings.append(RawFinding(
                    file=f"package.json#{adv.get('module_name', adv_id)}",
                    rule_id=f"npm:{adv.get('id', adv_id)}",
                    message=adv.get("title", ""),
                    tool="npm-audit",
                    engine="dependency",
                    raw_severity=adv.get("severity", "moderate"),
                    line=None,
                    col=None,
                    extra={
                        "url": adv.get("url"),
                        "suggestion": adv.get("recommendation"),
                        "tags": ["dependency"],
                    },
                ))
            except Exception as exc:
                logger.debug("npm audit v1 item parse error: %s", exc)
        return findings
