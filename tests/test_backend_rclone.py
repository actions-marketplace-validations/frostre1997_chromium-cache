import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from backends.base import BackendContext  # noqa: E402
from backends.rclone import RcloneBackend  # noqa: E402

HAS_RCLONE = shutil.which("rclone") is not None
pytestmark = pytest.mark.skipif(not HAS_RCLONE, reason="rclone not installed")


def _ctx(tmp_path, version="131.0.6778.85", exclude=None, extra=None):
    work = tmp_path / "work"
    return BackendContext(
        version=version,
        workdir=work,
        src_path=work / "src",
        config={"remote": "", "path": str(tmp_path / "cache"), **(extra or {})},
        exclude=exclude or [],
    )


def _make_fake_tree(work: Path):
    work.mkdir(parents=True, exist_ok=True)
    (work / ".gclient").write_text("solutions = []\n")
    (work / "src" / ".git").mkdir(parents=True)
    (work / "src" / "README").write_text("hello")
    (work / "src" / "build").mkdir()
    (work / "src" / "build" / "main.cc").write_text("int main(){}")
    (work / "out").mkdir()
    (work / "out" / "binary").write_text("x" * 512)


def test_restore_miss(tmp_path):
    assert RcloneBackend().restore(_ctx(tmp_path)) is False


def test_save_then_restore_roundtrip(tmp_path):
    ctx = _ctx(tmp_path)
    _make_fake_tree(ctx.workdir)
    backend = RcloneBackend()

    backend.save(ctx)
    assert backend.probe(ctx) > 0
    assert (tmp_path / "cache" / ctx.version / "src" / ".git").exists()

    shutil.rmtree(ctx.workdir)
    assert backend.restore(ctx) is True
    assert (ctx.workdir / "src" / "README").read_text() == "hello"
    assert (ctx.workdir / "src" / "build" / "main.cc").exists()


def test_save_applies_excludes(tmp_path):
    ctx = _ctx(tmp_path, exclude=["out/**"])
    _make_fake_tree(ctx.workdir)
    RcloneBackend().save(ctx)
    cache = tmp_path / "cache" / ctx.version
    assert not (cache / "out").exists()
    assert (cache / "src" / "README").exists()


def test_save_refuses_without_source(tmp_path):
    ctx = _ctx(tmp_path)
    (ctx.workdir / "out").mkdir(parents=True)
    with pytest.raises(SystemExit):
        RcloneBackend().save(ctx)


def test_probe_empty(tmp_path):
    assert RcloneBackend().probe(_ctx(tmp_path)) == 0.0
