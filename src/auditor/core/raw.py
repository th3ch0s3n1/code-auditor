"""RawFinding — intermediate representation produced by each parser.

All parsers emit RawFinding objects; the Normalizer converts them to Issue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawFinding:
    file: str
    rule_id: str
    message: str
    tool: str           # ruff | bandit | semgrep | eslint | npm-audit
    engine: str         # python | django | react | dependency
    raw_severity: str   # tool-native severity string (e.g. "HIGH", "2", "error")
    line: Optional[int] = None
    col: Optional[int] = None
    code_snippet: Optional[str] = None
    extra: dict = field(default_factory=dict)
