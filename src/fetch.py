"""Chromium source fetch + tag checkout."""
import os
import subprocess
from pathlib import Path

from lib.log import log, die
from lib import git, depot_tools


def _run(cmd: list[str], cwd: Path) -> None:
    log("run: " + " ".join(cmd) + f"  (cwd={cwd})")
    subprocess.run(cmd, cwd=str(cwd), check=True, text=True)


def _fetch_fresh(workdir: Path, shallow: bool) -> None:
    """Run `fetch chromium` in workdir. Creates workdir/src + workdir/.gclient."""
    depot_tools.ensure()
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = ["fetch"]
    if shallow:
        cmd.append("--no-history")
    cmd.extend(["--nohooks", "chromium"])
    _run(cmd, workdir)


def _checkout_tag(src: Path, version: str, shallow: bool) -> None:
    """Fetch + checkout the exact tag in src/."""
    tag_ref = f"refs/tags/{version}"
    fetch_args = ["fetch"]
    if shallow:
        fetch_args.extend(["--depth", "1"])
    fetch_args.extend(["origin", f"{tag_ref}:{tag_ref}"])
    git.run(fetch_args, cwd=src, check=False)
    git.run(["checkout", "--detach", tag_ref], cwd=src)


def ensure_at_version(workdir: Path, version: str, shallow: bool) -> None:
    """Idempotently ensure workdir/src is at the exact Chromium tag."""
    if os.environ.get("CHROMIUM_CACHE_SKIP_FETCH") == "1":
        if not (workdir / "src" / ".git").exists():
            die(
                f"fetch: CHROMIUM_CACHE_SKIP_FETCH=1 but no source at "
                f"{workdir}/src/.git"
            )
        log("fetch: skipped (CHROMIUM_CACHE_SKIP_FETCH=1)")
        return

    src = workdir / "src"
    if not (src / ".git").exists():
        log(f"fetch: fresh clone into {workdir}")
        _fetch_fresh(workdir, shallow)
    else:
        log(f"fetch: src exists at {src}, refreshing to {version}")
    _checkout_tag(src, version, shallow)
