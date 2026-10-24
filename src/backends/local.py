"""Local filesystem backend — for self-hosted runners with persistent disk."""
import shutil
from fnmatch import fnmatch
from pathlib import Path

from lib.log import log, die
from backends.base import Backend, BackendContext

GB = 1024 ** 3


def _root(config: dict) -> Path:
    root = config.get("root")
    if not root:
        die("local backend requires backend-config.root")
    return Path(root)


def _make_ignore(excludes: list[str], base: Path):
    """shutil.copytree ignore-callable: drop any name matching an exclude glob."""
    if not excludes:
        return None

    def ignore(src_dir: str, names: list[str]):
        ignored: set[str] = set()
        src = Path(src_dir)
        for name in names:
            full = src / name
            rel = full.relative_to(base).as_posix()
            for pattern in excludes:
                pat = pattern.rstrip("/")
                if "/" in pat:
                    if fnmatch(rel, pat):
                        ignored.add(name)
                        break
                else:
                    if fnmatch(name, pat):
                        ignored.add(name)
                        break
        return ignored

    return ignore


def _du_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


class LocalBackend(Backend):
    def restore(self, ctx: BackendContext) -> bool:
        src = _root(ctx.config) / ctx.version
        if not (src / "src" / ".git").exists():
            log(f"local: miss at {src}")
            return False
        if ctx.workdir.exists():
            shutil.rmtree(ctx.workdir)
        log(f"local: hit, copying {src} -> {ctx.workdir}")
        shutil.copytree(src, ctx.workdir)
        return True

    def save(self, ctx: BackendContext) -> None:
        dest = _root(ctx.config) / ctx.version
        if not (ctx.workdir / "src" / ".git").exists():
            die(f"local: refusing to save — no Chromium source at {ctx.workdir}/src/.git")
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        log(f"local: saving {ctx.workdir} -> {dest}"
            + (f" (excluding {len(ctx.exclude)} pattern(s))" if ctx.exclude else ""))
        shutil.copytree(ctx.workdir, dest, ignore=_make_ignore(ctx.exclude, ctx.workdir))

    def probe(self, ctx: BackendContext) -> float:
        src = _root(ctx.config) / ctx.version
        if not src.exists():
            return 0.0
        return _du_bytes(src) / GB
