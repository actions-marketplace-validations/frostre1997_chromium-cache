import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_main_runs(tmp_path):
    out_file = tmp_path / "out"
    sum_file = tmp_path / "sum"
    out_file.touch()
    sum_file.touch()

    env = os.environ.copy()
    env.update({
        "INPUT_MODE": "restore",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_MIN_FREE_GB": "10",
        "INPUT_PATH": str(tmp_path / "chromium"),
        "GITHUB_WORKSPACE": str(tmp_path),
        "GITHUB_OUTPUT": str(out_file),
        "GITHUB_STEP_SUMMARY": str(sum_file),
    })

    r = subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py")],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr

    out = out_file.read_text()
    assert "cache-hit=false" in out
    assert "version=131.0.6778.85" in out
    assert f"path={tmp_path}/chromium/src" in out
    assert "remote-size-gb=0" in out

    s = sum_file.read_text()
    assert "## chromium-cache" in s
    assert "131.0.6778.85" in s
    assert "local" in s


def test_main_invalid_mode(tmp_path):
    env = os.environ.copy()
    env.update({
        "INPUT_MODE": "banana",
        "GITHUB_WORKSPACE": str(tmp_path),
    })
    r = subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py")],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "mode must be one of" in r.stderr
