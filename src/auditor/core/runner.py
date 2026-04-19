"""Async subprocess runner used by every engine."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    cmd: list[str]
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        """Most linters exit non-zero when findings exist — that is expected."""
        return self.returncode >= 0

    @property
    def timed_out(self) -> bool:
        return self.returncode == -1

    @property
    def not_found(self) -> bool:
        return self.returncode == -2


class AsyncRunner:
    """Run external commands asynchronously, capturing stdout/stderr."""

    async def run(
        self,
        cmd: list[str],
        cwd: str | None = None,
        timeout: int = 300,
        extra_env: dict[str, str] | None = None,
    ) -> RunResult:
        logger.debug("Exec: %s", " ".join(cmd))
        try:
            run_env = os.environ.copy()
            if extra_env:
                run_env.update(extra_env)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=run_env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning("Timed out (%ds): %s", timeout, " ".join(cmd))
                return RunResult(
                    cmd=cmd, stdout="", stderr=f"Timeout after {timeout}s", returncode=-1
                )

            return RunResult(
                cmd=cmd,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                returncode=proc.returncode if proc.returncode is not None else 0,
            )

        except FileNotFoundError:
            logger.debug("Tool not found: %s", cmd[0])
            return RunResult(
                cmd=cmd, stdout="", stderr=f"Tool not found: {cmd[0]}", returncode=-2
            )
        except Exception as exc:
            logger.error("Runner error for %s: %s", cmd[0], exc)
            return RunResult(cmd=cmd, stdout="", stderr=str(exc), returncode=-3)
