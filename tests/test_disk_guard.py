import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import disk_guard  # noqa: E402
from lib.disk import DiskInfo, GB  # noqa: E402


def _fake_info(path: str, free_gb: float, total_gb: float) -> DiskInfo:
    return DiskInfo(path=path, measured=path, free_gb=free_gb, total_gb=total_gb)


def test_skip_when_probe_only(tmp_path):
    with patch("disk_guard.measure") as m:
        assert disk_guard.check(30, str(tmp_path), probe_only=True) is None
    m.assert_not_called()


def test_skip_when_min_zero(tmp_path):
    with patch("disk_guard.measure") as m:
        assert disk_guard.check(0, str(tmp_path), probe_only=False) is None
    m.assert_not_called()


def test_pass_when_enough(tmp_path):
    with patch("disk_guard.measure",
               return_value=_fake_info(str(tmp_path), 100.0, 200.0)):
        info = disk_guard.check(30, str(tmp_path), probe_only=False)
    assert info is not None
    assert info.free_gb == 100.0


def test_fail_when_short(tmp_path, capsys):
    with patch("disk_guard.measure",
               return_value=_fake_info(str(tmp_path), 5.0, 200.0)):
        with pytest.raises(SystemExit) as ei:
            disk_guard.check(30, str(tmp_path), probe_only=False)
    assert ei.value.code == 1
    err = capsys.readouterr().err
    assert "insufficient disk" in err
    assert "need >= 30 GB" in err
    assert "have 5.00 GB" in err
    assert "cleanser" in err
    assert "min-free-gb: 0" in err


def test_fail_when_target_exceeds_total(tmp_path, capsys):
    with patch("disk_guard.measure",
               return_value=_fake_info(str(tmp_path), 50.0, 84.0)):
        with pytest.raises(SystemExit) as ei:
            disk_guard.check(200, str(tmp_path), probe_only=False)
    assert ei.value.code == 1
    err = capsys.readouterr().err
    assert "exceeds total volume size" in err
    assert "84.00 GB" in err
