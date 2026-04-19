"""Ruff engine — fast Python linter."""

from __future__ import annotations

import logging
from pathlib import Path

from ...core.raw import RawFinding
from ...parsers.ruff_parser import RuffParser
from ..base import EngineBase

logger = logging.getLogger(__name__)


class RuffEngine(EngineBase):
    name = "ruff"
    engine_type = "python"

    _CONFIG = Path(__file__).parents[4] / "config" / "ruff.toml"

    async def run(self, path: Path) -> list[RawFinding]:
        cmd = [
            "ruff", "check",
            "--output-format", "json",
            "--no-cache",
        ]
        if self._CONFIG.exists():
            cmd += ["--config", str(self._CONFIG)]
        cmd.append(str(path))

        result = await self.runner.run(cmd, cwd=str(path))

        if result.not_found:
            logger.debug("ruff not found — skipping")
            return []
        if result.timed_out:
            logger.warning("ruff timed out")
            return []

        return RuffParser().parse(result.stdout, base_path=path)
