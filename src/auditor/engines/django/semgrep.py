"""Semgrep engine — semantic code analysis (Django rules)."""

from __future__ import annotations

import logging
from pathlib import Path

from ...core.raw import RawFinding
from ...parsers.semgrep_parser import SemgrepParser
from ..base import EngineBase

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parents[4] / "config" / "semgrep"


class SemgrepEngine(EngineBase):
    name = "semgrep"
    engine_type = "django"

    async def run(self, path: Path) -> list[RawFinding]:
        configs = list(_CONFIG_DIR.glob("*.yml")) if _CONFIG_DIR.exists() else []

        if not configs:
            # Fall back to the official Django ruleset
            configs_args = ["--config", "p/django"]
        else:
            configs_args = []
            for cfg in configs:
                configs_args += ["--config", str(cfg)]

        cmd = [
            "semgrep",
            "--json",
            "--quiet",
            *configs_args,
            str(path),
        ]
        result = await self.runner.run(cmd, cwd=str(path), timeout=180)

        if result.not_found:
            logger.debug("semgrep not found — skipping")
            return []
        if result.timed_out:
            logger.warning("semgrep timed out")
            return []

        return SemgrepParser().parse(result.stdout, base_path=path)
