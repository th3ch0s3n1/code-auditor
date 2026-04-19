"""ESLint engine — JavaScript/React linter."""

from __future__ import annotations

import logging
from pathlib import Path

from ...core.raw import RawFinding
from ...parsers.eslint_parser import ESLintParser
from ..base import EngineBase

logger = logging.getLogger(__name__)

_ESLINT_CFG = Path(__file__).parents[4] / "config" / "eslint" / ".eslintrc.json"


class ESLintEngine(EngineBase):
    name = "eslint"
    engine_type = "react"

    def __init__(self, react_root: Path | None = None):
        super().__init__()
        self._react_root = react_root

    @property
    def _cli_cmd(self) -> str:
        return "eslint"

    async def run(self, path: Path) -> list[RawFinding]:
        cwd = str(self._react_root or path)

        cmd = ["eslint", "--format", "json"]
        if _ESLINT_CFG.exists():
            cmd += ["--no-eslintrc", "--config", str(_ESLINT_CFG)]
        # Scan all JS/JSX/TS/TSX files
        cmd += ["--ext", ".js,.jsx,.ts,.tsx", str(self._react_root or path)]

        result = await self.runner.run(cmd, cwd=cwd, timeout=120)

        if result.not_found:
            logger.debug("eslint not found — skipping")
            return []
        if result.timed_out:
            logger.warning("eslint timed out")
            return []

        return ESLintParser().parse(result.stdout, base_path=path)
