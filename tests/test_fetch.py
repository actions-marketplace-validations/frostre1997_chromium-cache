import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import fetch as fetch_mod  # noqa: E402


def test_skip_fetch_without_source(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMIUM_CACHE_SKIP_FETCH", "1")
    with pytest.raises(SystemExit):
        fetch_mod.ensure_at_version(tmp_path / "chromium", "131.0.6778.85", shallow=True)


def test_skip_fetch_with_source(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMIUM_CACHE_SKIP_FETCH", "1")
    (tmp_path / "src" / ".git").mkdir(parents=True)
    fetch_mod.ensure_at_version(tmp_path, "131.0.6778.85", shallow=True)


def test_ensure_at_version_fresh(tmp_path, monkeypatch):
    monkeypatch.delenv("CHROMIUM_CACHE_SKIP_FETCH", raising=False)
    workdir = tmp_path / "chromium"

    def fake_run(cmd, cwd):
        if "chromium" in cmd and cmd[0] == "fetch":
            (workdir / "src" / ".git").mkdir(parents=True, exist_ok=True)

    with patch.object(fetch_mod, "_run", side_effect=fake_run), \
         patch.object(fetch_mod.depot_tools, "ensure", return_value=Path("/fake")), \
         patch.object(fetch_mod.git, "run") as git_run:
        fetch_mod.ensure_at_version(workdir, "131.0.6778.85", shallow=True)

    git_calls = [c.args[0] for c in git_run.call_args_list]
    assert any("fetch" in c for c in git_calls)
    assert any("checkout" in c for c in git_calls)


def test_ensure_at_version_existing(tmp_path, monkeypatch):
    monkeypatch.delenv("CHROMIUM_CACHE_SKIP_FETCH", raising=False)
    workdir = tmp_path / "chromium"
    (workdir / "src" / ".git").mkdir(parents=True)

    with patch.object(fetch_mod, "_run") as fresh, \
         patch.object(fetch_mod.depot_tools, "ensure", return_value=Path("/fake")), \
         patch.object(fetch_mod.git, "run") as git_run:
        fetch_mod.ensure_at_version(workdir, "131.0.6778.85", shallow=True)

    fresh.assert_not_called()
    git_calls = [c.args[0] for c in git_run.call_args_list]
    assert any("checkout" in c for c in git_calls)
