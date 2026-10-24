import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(tmp_path, env_extra):
    out_file = tmp_path / "out"
    sum_file = tmp_path / "sum"
    out_file.touch()
    sum_file.touch()
    env = os.environ.copy()
    env.update({
        "GITHUB_OUTPUT": str(out_file),
        "GITHUB_STEP_SUMMARY": str(sum_file),
        "GITHUB_WORKSPACE": str(tmp_path),
        **env_extra,
    })
    r = subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py")],
        env=env, capture_output=True, text=True,
    )
    return r, out_file.read_text(), sum_file.read_text()


def test_main_runs(tmp_path):
    r, out, s = _run(tmp_path, {
        "INPUT_MODE": "restore",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_MIN_FREE_GB": "1",
        "INPUT_PATH": str(tmp_path / "chromium"),
    })
    assert r.returncode == 0, r.stderr
    assert "cache-hit=false" in out
    assert "version=131.0.6778.85" in out
    assert f"path={tmp_path}/chromium/src" in out
    assert "remote-size-gb=0" in out
    assert "## chromium-cache" in s
    assert "131.0.6778.85" in s
    assert "local" in s
    assert "Disk:" in s


def test_main_invalid_mode(tmp_path):
    r, _, _ = _run(tmp_path, {"INPUT_MODE": "banana"})
    assert r.returncode != 0
    assert "mode must be one of" in r.stderr


def test_main_fails_on_disk_shortfall(tmp_path):
    r, out, _ = _run(tmp_path, {
        "INPUT_MODE": "restore",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_MIN_FREE_GB": "999999999",       # no device has this much
        "INPUT_PATH": str(tmp_path / "chromium"),
    })
    assert r.returncode != 0
    assert "insufficient disk" in r.stderr
    assert "exceeds total volume size" in r.stderr
    # Fail before writing outputs
    assert "cache-hit" not in out


def test_main_probe_skips_disk(tmp_path):
    r, out, _ = _run(tmp_path, {
        "INPUT_MODE": "both",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_MIN_FREE_GB": "999999999",
        "INPUT_PROBE_ONLY": "true",
        "INPUT_PATH": str(tmp_path / "chromium"),
    })
    assert r.returncode == 0, r.stderr
    assert "cache-hit=false" in out
    assert "skipped (probe-only)" in r.stderr
