import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import gclient as gclient_mod  # noqa: E402


def test_skip_sync(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMIUM_CACHE_SKIP_FETCH", "1")
    with patch("subprocess.run") as sub:
        gclient_mod.sync(tmp_path, shallow=True)
    sub.assert_not_called()


def test_sync_runs_gclient(tmp_path, monkeypatch):
    monkeypatch.delenv("CHROMIUM_CACHE_SKIP_FETCH", raising=False)
    (tmp_path / "src" / ".git").mkdir(parents=True)

    with patch.object(gclient_mod.depot_tools, "ensure", return_value=Path("/fake")), \
         patch("subprocess.run") as sub:
        gclient_mod.sync(tmp_path, shallow=True)

    sub.assert_called_once()
    cmd = sub.call_args.args[0]
    assert cmd[0] == "gclient"
    assert cmd[1] == "sync"
    assert "--no-history" in cmd
    assert "-D" in cmd
    assert "--reset" in cmd


def test_sync_no_shallow(tmp_path, monkeypatch):
    monkeypatch.delenv("CHROMIUM_CACHE_SKIP_FETCH", raising=False)
    (tmp_path / "src" / ".git").mkdir(parents=True)

    with patch.object(gclient_mod.depot_tools, "ensure", return_value=Path("/fake")), \
         patch("subprocess.run") as sub:
        gclient_mod.sync(tmp_path, shallow=False)

    cmd = sub.call_args.args[0]
    assert "--no-history" not in cmd
