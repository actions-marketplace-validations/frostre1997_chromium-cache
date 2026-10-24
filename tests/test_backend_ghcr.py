import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from backends.base import BackendContext  # noqa: E402
from backends.ghcr import GhcrBackend  # noqa: E402

HAS_ZSTD = shutil.which("zstd") is not None
HAS_SPLIT = shutil.which("split") is not None
HAS_TAR = shutil.which("tar") is not None
HAS_UNIX_PIPE_TOOLS = HAS_ZSTD and HAS_SPLIT and HAS_TAR


def _ctx(tmp_path, version="131.0.6778.85"):
    work = tmp_path / "work"
    return BackendContext(
        version=version,
        workdir=work,
        src_path=work / "src",
        config={"registry": "ghcr.io", "repository": "frostre1997/test"},
        exclude=[],
        shallow=True,
    )


def _make_fake_tree(work: Path):
    work.mkdir(parents=True, exist_ok=True)
    (work / ".gclient").write_text("solutions = []\n")
    (work / "src" / ".git").mkdir(parents=True)
    (work / "src" / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (work / "src" / "README").write_text("hello")
    (work / "src" / "build").mkdir()
    (work / "src" / "build" / "main.cc").write_text("int main(){}")


def test_restore_miss(tmp_path):
    with patch("backends.ghcr._oras_exists", return_value=False):
        assert GhcrBackend().restore(_ctx(tmp_path)) is False


def test_probe_empty(tmp_path):
    with patch("backends.ghcr._oras_exists", return_value=False):
        assert GhcrBackend().probe(_ctx(tmp_path)) == 0.0


def test_probe_size(tmp_path):
    manifest = {"layers": [{"size": 1073741824}, {"size": 536870912}]}
    with patch("backends.ghcr._oras_exists", return_value=True), \
         patch("backends.ghcr._oras_manifest", return_value=manifest):
        size = GhcrBackend().probe(_ctx(tmp_path))
    assert size == pytest.approx(1.5, rel=1e-4)


def test_save_requires_source(tmp_path):
    ctx = _ctx(tmp_path)
    (ctx.workdir / "out").mkdir(parents=True)
    with patch("backends.ghcr._oras_login"):
        with pytest.raises(SystemExit):
            GhcrBackend().save(ctx)


@pytest.mark.skipif(not HAS_UNIX_PIPE_TOOLS, reason="zstd/split/tar not installed")
def test_save_creates_parts_and_pushes(tmp_path):
    ctx = _ctx(tmp_path)
    _make_fake_tree(ctx.workdir)
    captured = {}

    def fake_push(config, version, files, cwd):
        captured["ref"] = f"{config['registry']}/{config['repository']}:{version}"
        captured["files"] = [f.name for f in files]
        assert all(f.exists() for f in files)

    with patch("backends.ghcr._oras_login"), \
         patch("backends.ghcr._oras_push", side_effect=fake_push):
        GhcrBackend().save(ctx)

    assert captured["ref"] == "ghcr.io/frostre1997/test:131.0.6778.85"
    assert len(captured["files"]) >= 1
    assert all(n.startswith("chromium.tar.zst.part-") for n in captured["files"])


@pytest.mark.skipif(not HAS_UNIX_PIPE_TOOLS, reason="zstd/split/tar not installed")
def test_restore_from_parts(tmp_path):
    src = tmp_path / "src"
    _make_fake_tree(src)

    parts_dir = tmp_path / "remote_parts"
    parts_dir.mkdir()
    archive = parts_dir / "chromium.tar.zst"

    with archive.open("wb") as out:
        tar = subprocess.Popen(["tar", "-C", str(src), "-cf", "-", "."], stdout=subprocess.PIPE)
        zstd = subprocess.Popen(["zstd", "-q", "-c"], stdin=tar.stdout, stdout=out)
        tar.stdout.close()
        zstd.communicate()
        tar.wait()
    assert zstd.returncode == 0 and tar.returncode == 0

    GhcrBackend._split(archive, parts_dir)

    ctx = _ctx(tmp_path)
    assert not ctx.workdir.exists()

    def fake_pull(config, version, dest):
        for p in parts_dir.glob("chromium.tar.zst.part-*"):
            shutil.copy(p, Path(dest) / p.name)

    with patch("backends.ghcr._oras_exists", return_value=True), \
         patch("backends.ghcr._oras_login"), \
         patch("backends.ghcr._oras_pull", side_effect=fake_pull):
        assert GhcrBackend().restore(ctx) is True

    assert (ctx.workdir / "src" / "README").read_text() == "hello"
    assert (ctx.workdir / "src" / ".git" / "HEAD").read_text() == "ref: refs/heads/main\n"
    assert (ctx.workdir / ".gclient").read_text() == "solutions = []\n"
