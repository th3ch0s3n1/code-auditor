"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_django_dir() -> Path:
    return FIXTURES_DIR / "sample_django"


@pytest.fixture
def sample_react_dir() -> Path:
    return FIXTURES_DIR / "sample_react"
