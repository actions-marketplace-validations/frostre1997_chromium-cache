import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from lib import disk  # noqa: E402


class FakeStatVFS:
    def __init__(self, blocks: int, bavail: int, frsize: int = 4096):
        self.f_blocks = blocks
        self.f_bavail = bavail
        self.f_frsize = frsize


def test_measure_existing_path(tmp_path):
    with patch("os.statvfs", return_value=FakeStatVFS(blocks=1000, bavail=500)):
        info = disk.measure(str(tmp_path))
    assert info.path == str(tmp_path)
    assert info.measured == str(tmp_path)
    assert info.free_gb == pytest.approx(500 * 4096 / disk.GB, rel=1e-4)
    assert info.total_gb == pytest.approx(1000 * 4096 / disk.GB, rel=1e-4)


def test_measure_walks_up_for_nonexistent_path(tmp_path):
    target = tmp_path / "does" / "not" / "exist" / "chromium"
    with patch("os.statvfs", return_value=FakeStatVFS(blocks=100, bavail=50)):
        info = disk.measure(str(target))
    assert info.path == str(target)
    assert info.measured == str(tmp_path)


def test_nearest_existing_returns_root_when_nothing(tmp_path):
    # Even an absurd path should land on an existing ancestor
    p = "/definitely-does-not-exist-xyz/abc"
    assert disk.nearest_existing(p) in ("/", p)


def test_nearest_existing_idempotent(tmp_path):
    assert disk.nearest_existing(str(tmp_path)) == str(tmp_path)


def test_measure_real_filesystem():
    # Real statvfs on cwd — Termux reports real Android free space
    info = disk.measure(os.getcwd())
    assert info.free_gb >= 0
    assert info.total_gb > 0
    assert info.free_gb <= info.total_gb
