import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from backends.base import BackendContext  # noqa: E402
from backends.local import LocalBackend  # noqa: E402


def _ctx(tmp_path, version="131.0.6778.85", exclude=None):
    work = tmp_path / "work"
    return BackendContext(
        version=version,
        workdir=work,
        src_path=work / "src",
        config={"root": str(tmp_path / "cache")},
        exclude=exclude or [],
    )


def _make_fake_tree(work: Path):
    (work / "src" / ".git").mkdir(parents=True)
    (work / "src" / "README").write_text("hello")
    (work / "src" / "build").mkdir()
    (work / "src" / "build" / "main.cc").write_text("int main(){}")
    (work / "out").mkdir()
    (work / "out" / "binary").write_text("x" * 1024)


def test_restore_miss(tmp_path):
    ctx = _ctx(tmp_path)
    assert LocalBackend().restore(ctx) is False
    assert not ctx.workdir.exists()


def test_save_then_restore_roundtrip(tmp_path):
    ctx = _ctx(tmp_path)
    _make_fake_tree(ctx.workdir)
    backend = LocalBackend()

    backend.save(ctx)
    assert (tmp_path / "cache" / ctx.version / "src" / "README").exists()
    assert backend.probe(ctx) > 0

    import shutil
    shutil.rmtree(ctx.workdir)

    assert backend.restore(ctx) is True
    assert (ctx.workdir / "src" / "README").read_text() == "hello"
    assert (ctx.workdir / "src" / "build" / "main.cc").exists()


def test_save_applies_excludes(tmp_path):
    ctx = _ctx(tmp_path, exclude=["out/", "third_party/*/test"])
    (ctx.workdir / "src" / ".git").mkdir(parents=True)
    (ctx.workdir / "out").mkdir()
    (ctx.workdir / "out" / "binary").write_text("x")
    (ctx.workdir / "third_party" / "foo" / "test").mkdir(parents=True)
    (ctx.workdir / "third_party" / "foo" / "test" / "t.cc").write_text("x")
    (ctx.workdir / "third_party" / "foo" / "src").mkdir()
    (ctx.workdir / "third_party" / "foo" / "src" / "ok.cc").write_text("x")

    LocalBackend().save(ctx)

    cache = tmp_path / "cache" / ctx.version
    assert not (cache / "out").exists()
    assert not (cache / "third_party" / "foo" / "test").exists()
    assert (cache / "third_party" / "foo" / "src" / "ok.cc").exists()


def test_save_name_only_pattern_matches_anywhere(tmp_path):
    ctx = _ctx(tmp_path, exclude=["LayoutTests"])
    (ctx.workdir / "src" / ".git").mkdir(parents=True)
    (ctx.workdir / "src" / "LayoutTests").mkdir(parents=True)
    (ctx.workdir / "src" / "LayoutTests" / "t.html").write_text("x")
    (ctx.workdir / "third_party" / "foo" / "LayoutTests").mkdir(parents=True)
    (ctx.workdir / "third_party" / "foo" / "LayoutTests" / "t.html").write_text("x")
    (ctx.workdir / "src" / "keep.cc").write_text("x")

    LocalBackend().save(ctx)

    cache = tmp_path / "cache" / ctx.version
    assert not (cache / "src" / "LayoutTests").exists()
    assert not (cache / "third_party" / "foo" / "LayoutTests").exists()
    assert (cache / "src" / "keep.cc").exists()


def test_save_refuses_without_source(tmp_path):
    ctx = _ctx(tmp_path)  # no src/.git
    with pytest.raises(SystemExit):
        LocalBackend().save(ctx)


def test_probe_empty(tmp_path):
    ctx = _ctx(tmp_path)
    assert LocalBackend().probe(ctx) == 0.0
