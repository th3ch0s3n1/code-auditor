"""Project type detector.

Walks the target directory and identifies Python, Django, and React projects
so the pipeline can activate the relevant engines.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProjectInfo:
    path: Path
    has_python: bool = False
    has_django: bool = False
    has_react: bool = False
    python_root: Path | None = None
    react_root: Path | None = None
    project_types: list[str] = field(default_factory=list)


class ProjectDetector:
    """Detect what kind of project lives at *path*."""

    _PYTHON_MARKERS = ("requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "manage.py")

    def detect(self, path: str | Path) -> ProjectInfo:
        root = Path(path).resolve()
        info = ProjectInfo(path=root)

        self._detect_python(root, info)
        self._detect_react(root, info)

        if info.has_python:
            info.project_types.append("python")
        if info.has_django:
            info.project_types.append("django")
        if info.has_react:
            info.project_types.append("react")

        logger.debug("Detected project types %s at %s", info.project_types, root)
        return info

    # ── Python / Django ───────────────────────────────────────────────────────

    def _detect_python(self, root: Path, info: ProjectInfo) -> None:
        # Check root first
        if any((root / m).exists() for m in self._PYTHON_MARKERS):
            info.has_python = True
            info.python_root = root
        else:
            # One-level deep for monorepo / xsite-style layouts
            for sub in sorted(root.iterdir()):
                if sub.is_dir() and not sub.name.startswith("."):
                    if any((sub / m).exists() for m in self._PYTHON_MARKERS):
                        info.has_python = True
                        info.python_root = sub
                        break

        if not info.has_python:
            return

        scan_root = info.python_root or root

        # Django: manage.py is the definitive marker
        if (scan_root / "manage.py").exists():
            info.has_django = True
            return

        # Django: requirements.txt or pyproject.toml mentions django
        for req_file in [
            scan_root / "requirements.txt",
            scan_root / "requirements" / "base.txt",
            scan_root / "pyproject.toml",
        ]:
            if req_file.exists():
                content = req_file.read_text(encoding="utf-8", errors="ignore").lower()
                if "django" in content:
                    info.has_django = True
                    return

    # ── React ─────────────────────────────────────────────────────────────────

    def _detect_react(self, root: Path, info: ProjectInfo) -> None:
        candidates = [root]
        try:
            candidates += [
                sub for sub in root.iterdir()
                if sub.is_dir()
                and not sub.name.startswith(".")
                and sub.name not in ("node_modules", "__pycache__", ".venv", "venv")
            ]
        except PermissionError:
            pass

        for candidate in candidates:
            pkg = candidate / "package.json"
            if not pkg.exists():
                continue
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "react" in deps:
                    info.has_react = True
                    info.react_root = candidate
                    return
            except Exception:
                pass
