"""Engine base class."""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from ..core.raw import RawFinding
from ..core.runner import AsyncRunner


class EngineBase(ABC):
    """Abstract base for all scan engines."""

    def __init__(self):
        self.runner = AsyncRunner()

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used in RawFinding.tool (e.g. 'ruff')."""

    @property
    @abstractmethod
    def engine_type(self) -> str:
        """Logical engine group: python | django | react | dependency."""

    @abstractmethod
    async def run(self, path: Path) -> list[RawFinding]:
        """Execute the tool and return raw findings."""

    def is_available(self) -> bool:
        """Return True if the underlying CLI tool is on PATH."""
        return shutil.which(self._cli_cmd) is not None

    @property
    def _cli_cmd(self) -> str:
        """Override if the CLI binary name differs from self.name."""
        return self.name
