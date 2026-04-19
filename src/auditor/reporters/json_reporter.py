"""JSON reporter — emit ScanResult as a JSON document."""

from __future__ import annotations

import json
from pathlib import Path

from ..core.schema import ScanResult


def render(result: ScanResult, path: Path | None = None, pretty: bool = True) -> str:
    """Serialise *result* to JSON and optionally write it to *path*."""
    indent = 2 if pretty else None
    payload = json.dumps(result.model_dump(mode="json"), indent=indent, ensure_ascii=False)

    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")

    return payload
