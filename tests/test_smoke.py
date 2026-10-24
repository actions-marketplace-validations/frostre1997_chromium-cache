import json
import os
import shutil
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


def test_main_invalid_mode(tmp_path):
    r, _, _ = _run(tmp_path, {"INPUT_MODE": "banana"})
    assert r.returncode != 0
    assert "mode must be one of" in r.stderr


def test_main_fails_on_disk_shortfall(tmp_path):
    r, out, _ = _run(tmp_path, {
        "INPUT_MODE": "restore",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_MIN_FREE_GB": "999999999",
        "INPUT_PATH": str(tmp_path / "chromium"),
    })
    assert r.returncode != 0
    assert "insufficient disk" in r.stderr
    assert "exceeds total volume size" in r.stderr
    assert "cache-hit" not in out


def test_main_probe_skips_disk(tmp_path):
    r, out, s = _run(tmp_path, {
        "INPUT_MODE": "both",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_BACKEND_CONFIG": '{"root": "' + str(tmp_path / "cache") + '"}',
        "INPUT_MIN_FREE_GB": "999999999",
        "INPUT_PROBE_ONLY": "true",
        "INPUT_PATH": str(tmp_path / "chromium"),
    })
    assert r.returncode == 0, r.stderr
    assert "cache-hit=false" in out
    assert "remote-size-gb=0.00" in out
    assert "skipped (probe-only)" in r.stderr


def test_main_version_invalid(tmp_path):
    r, _, _ = _run(tmp_path, {
        "INPUT_MODE": "probe",
        "INPUT_VERSION": "not-a-version",
        "INPUT_BACKEND": "local",
        "INPUT_PROBE_ONLY": "true",
        "INPUT_PATH": str(tmp_path / "chromium"),
    })
    assert r.returncode != 0
    assert "not a valid Chromium version" in r.stderr


def test_roundtrip_local(tmp_path):
    work = tmp_path / "work"
    cache = tmp_path / "cache"
    work.mkdir()
    cache.mkdir()

    (work / "src" / ".git").mkdir(parents=True)
    (work / "src" / "README").write_text("hello")
    (work / "src" / "build").mkdir()
    (work / "src" / "build" / "main.cc").write_text("int main(){}")
    (work / "out").mkdir()
    (work / "out" / "binary").write_text("binary data")

    cfg = json.dumps({"root": str(cache)})

    r, out, s = _run(tmp_path, {
        "INPUT_MODE": "save",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_BACKEND_CONFIG": cfg,
        "INPUT_MIN_FREE_GB": "0",
        "INPUT_PATH": str(work),
        "INPUT_EXCLUDE": "out/",
        "CHROMIUM_CACHE_SKIP_FETCH": "1",
    })
    assert r.returncode == 0, r.stderr
    assert (cache / "131.0.6778.85" / "src" / ".git").exists()
    assert not (cache / "131.0.6778.85" / "out").exists()
    assert "remote-size-gb=" in out

    shutil.rmtree(work)

    r, out, s = _run(tmp_path, {
        "INPUT_MODE": "restore",
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_BACKEND_CONFIG": cfg,
        "INPUT_MIN_FREE_GB": "0",
        "INPUT_PATH": str(work),
        "CHROMIUM_CACHE_SKIP_FETCH": "1",
    })
    assert r.returncode == 0, r.stderr
    assert "cache-hit=true" in out
    assert "Cache hit: `yes`" in s
    assert (work / "src" / ".git").exists()
    assert (work / "src" / "README").read_text() == "hello"


def test_save_skipped_on_hit_without_force(tmp_path):
    work = tmp_path / "work"
    cache = tmp_path / "cache"
    work.mkdir()
    cache.mkdir()
    (work / "src" / ".git").mkdir(parents=True)
    (work / "src" / "x").write_text("hello")

    cfg = json.dumps({"root": str(cache)})
    env = {
        "INPUT_VERSION": "131.0.6778.85",
        "INPUT_BACKEND": "local",
        "INPUT_BACKEND_CONFIG": cfg,
        "INPUT_MIN_FREE_GB": "0",
        "INPUT_PATH": str(work),
        "CHROMIUM_CACHE_SKIP_FETCH": "1",
    }

    r, _, _ = _run(tmp_path, {"INPUT_MODE": "save", **env})
    assert r.returncode == 0, r.stderr

    (work / "src" / "x").write_text("CHANGED")
    r, out, _ = _run(tmp_path, {"INPUT_MODE": "both", **env})
    assert r.returncode == 0, r.stderr
    assert "cache-hit=true" in out
    assert "save: skipped" in r.stderr
    assert (cache / "131.0.6778.85" / "src" / "x").read_text() == "hello"
