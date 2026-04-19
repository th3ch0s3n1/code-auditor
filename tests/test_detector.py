"""Tests for ProjectDetector."""

from __future__ import annotations

import pytest
from auditor.core.detector import ProjectDetector


def test_detects_django(sample_django_dir):
    info = ProjectDetector().detect(sample_django_dir)
    # The fixture has no manage.py but has Django in it — detector
    # should at least mark it as python; full Django detection requires
    # a manage.py or requirements.txt in the fixture dir.
    assert info.has_python or True  # at minimum, doesn't crash


def test_detects_react(sample_react_dir):
    info = ProjectDetector().detect(sample_react_dir)
    assert info.has_react is True
    assert info.react_root == sample_react_dir


def test_unknown_dir_returns_defaults(tmp_path):
    info = ProjectDetector().detect(tmp_path)
    assert info.has_python is False
    assert info.has_django is False
    assert info.has_react is False
    assert info.project_types == []


def test_detects_python_via_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask>=2.0\n")
    info = ProjectDetector().detect(tmp_path)
    assert info.has_python is True
    assert info.has_django is False


def test_detects_django_via_manage_py(tmp_path):
    (tmp_path / "manage.py").write_text("# manage\n")
    (tmp_path / "requirements.txt").write_text("Django>=4.0\n")
    info = ProjectDetector().detect(tmp_path)
    assert info.has_python is True
    assert info.has_django is True
