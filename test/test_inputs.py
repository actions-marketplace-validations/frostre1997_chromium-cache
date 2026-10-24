import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import inputs as inputs_mod  # noqa: E402


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in list(os.environ):
        if k.startswith("INPUT_") or k == "GITHUB_WORKSPACE":
            monkeypatch.delenv(k, raising=False)


def test_defaults(monkeypatch):
    monkeypatch.setenv("GITHUB_WORKSPACE", "/tmp/ws")
    inp = inputs_mod.parse()
    assert inp.mode == "both"
    assert inp.backend == "ghcr"
    assert inp.path == "/tmp/ws/chromium"
    assert inp.min_free_gb == 30
    assert inp.shallow is True
    assert inp.probe_only is False
    assert inp.force_save is False


def test_mode_invalid(monkeypatch):
    monkeypatch.setenv("INPUT_MODE", "banana")
    with pytest.raises(SystemExit):
        inputs_mod.parse()


def test_backend_invalid(monkeypatch):
    monkeypatch.setenv("INPUT_BACKEND", "ftp")
    with pytest.raises(SystemExit):
        inputs_mod.parse()


def test_min_free_gb_non_int(monkeypatch):
    monkeypatch.setenv("INPUT_MIN_FREE_GB", "abc")
    with pytest.raises(SystemExit):
        inputs_mod.parse()


def test_min_free_gb_negative(monkeypatch):
    monkeypatch.setenv("INPUT_MIN_FREE_GB", "-1")
    with pytest.raises(SystemExit):
        inputs_mod.parse()


def test_backend_config_object(monkeypatch):
    monkeypatch.setenv("GITHUB_WORKSPACE", "/tmp/ws")
    monkeypatch.setenv("INPUT_BACKEND_CONFIG", '{"remote": "r2", "path": "x"}')
    inp = inputs_mod.parse()
    assert inp.backend_config == {"remote": "r2", "path": "x"}


def test_backend_config_invalid_json(monkeypatch):
    monkeypatch.setenv("INPUT_BACKEND_CONFIG", "not-json")
    with pytest.raises(SystemExit):
        inputs_mod.parse()


def test_backend_config_not_object(monkeypatch):
    monkeypatch.setenv("INPUT_BACKEND_CONFIG", '[1, 2]')
    with pytest.raises(SystemExit):
        inputs_mod.parse()


def test_exclude_split(monkeypatch):
    monkeypatch.setenv("GITHUB_WORKSPACE", "/tmp/ws")
    monkeypatch.setenv("INPUT_EXCLUDE", "out/, third_party/*/test, LayoutTests")
    inp = inputs_mod.parse()
    assert inp.exclude == ["out/", "third_party/*/test", "LayoutTests"]


def test_bool_parsing(monkeypatch):
    monkeypatch.setenv("GITHUB_WORKSPACE", "/tmp/ws")
    monkeypatch.setenv("INPUT_SHALLOW", "false")
    inp = inputs_mod.parse()
    assert inp.shallow is False


def test_relative_path_resolved(monkeypatch):
    monkeypatch.setenv("GITHUB_WORKSPACE", "/tmp/ws")
    monkeypatch.setenv("INPUT_PATH", "src/chromium")
    inp = inputs_mod.parse()
    assert inp.path == "/tmp/ws/src/chromium"


def test_empty_path_without_workspace(monkeypatch):
    with pytest.raises(SystemExit):
        inputs_mod.parse()
