"""npm audit engine — Node.js dependency vulnerability scanner."""

from __future__ import annotations

import logging
from pathlib import Path

from ...core.raw import RawFinding
from ...parsers.npm_audit_parser import NpmAuditParser
from ..base import EngineBase

logger = logging.getLogger(__name__)


class NpmAuditEngine(EngineBase):
    name = "npm-audit"
    engine_type = "dependency"

    def __init__(self, react_root: Path | None = None):
        super().__init__()
        self._react_root = react_root

    @property
    def _cli_cmd(self) -> str:
        return "npm"

    def is_available(self) -> bool:
        import shutil
        return shutil.which("npm") is not None

    async def run(self, path: Path) -> list[RawFinding]:
        cwd = str(self._react_root or path)

        result = await self.runner.run(
            ["npm", "audit", "--json"],
            cwd=cwd,
            timeout=120,
        )

        if result.not_found:
            logger.debug("npm not found — skipping")
            return []
        if result.timed_out:
            logger.warning("npm audit timed out")
            return []

        return NpmAuditParser().parse(result.stdout, base_path=path)
