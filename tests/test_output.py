import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import outputs as outputs_mod  # noqa: E402


def test_write_no_path(monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    outputs_mod.write(**{"cache-hit": "false"})  # must not raise


def test_write_appends(tmp_path, monkeypatch):
    f = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(f))
    outputs_mod.write(**{"cache-hit": "false", "path": "/x/src"})
    outputs_mod.write(**{"version": "131.0.6778.85"})
    content = f.read_text()
    assert "cache-hit=false" in content
    assert "path=/x/src" in content
    assert "version=131.0.6778.85" in content
