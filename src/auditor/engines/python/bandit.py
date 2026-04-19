"""Bandit engine — Python security linter."""

from __future__ import annotations

import logging
from pathlib import Path

from ...core.raw import RawFinding
from ...parsers.bandit_parser import BanditParser
from ..base import EngineBase

logger = logging.getLogger(__name__)


class BanditEngine(EngineBase):
    name = "bandit"
    engine_type = "python"

    async def run(self, path: Path) -> list[RawFinding]:
        cmd = [
            "bandit",
            "--recursive",
            "--format", "json",
            "--quiet",
            str(path),
        ]
        result = await self.runner.run(cmd, cwd=str(path))

        if result.not_found:
            logger.debug("bandit not found — skipping")
            return []
        if result.timed_out:
            logger.warning("bandit timed out")
            return []
        # bandit exits 1 when issues are found — that is expected
        return BanditParser().parse(result.stdout, base_path=path)
