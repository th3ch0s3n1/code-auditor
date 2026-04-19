"""File hash cache — skip unchanged files on incremental re-scans."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_DIR = ".auditor_cache"
_CACHE_FILE = "file_hashes.json"


class FileHashCache:
    """Persist SHA-256 hashes so unchanged files can be skipped."""

    def __init__(self, base_dir: Path, enabled: bool = True):
        self.enabled = enabled
        self._cache_dir = base_dir / _CACHE_DIR
        self._cache_file = self._cache_dir / _CACHE_FILE
        self._data: dict[str, str] = {}
        if enabled:
            self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def is_changed(self, path: Path) -> bool:
        """Return True if the file has changed since the last scan (or cache is disabled)."""
        if not self.enabled:
            return True
        key = str(path)
        try:
            current = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return True
        changed = self._data.get(key) != current
        if changed:
            self._data[key] = current
        return changed

    def save(self) -> None:
        if not self.enabled:
            return
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_file.write_text(json.dumps(self._data, indent=2))

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._cache_file.exists():
            try:
                self._data = json.loads(self._cache_file.read_text())
            except Exception as exc:
                logger.debug("Could not load cache: %s", exc)
                self._data = {}
