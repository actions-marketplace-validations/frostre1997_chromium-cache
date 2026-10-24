"""gclient sync wrapper."""
import os
import subprocess
from pathlib import Path

from lib.log import log, die
from lib import depot_tools


def sync(workdir: Path, shallow: bool) -> None:
    """Run gclient sync in workdir (parent of src/)."""
    if os.environ.get("CHROMIUM_CACHE_SKIP_FETCH") == "1":
        log("gclient: skipped (CHROMIUM_CACHE_SKIP_FETCH=1)")
        return

    if not (workdir / ".gclient").exists() and not (workdir / "src" / ".git").exists():
        die(f"gclient: no Chromium checkout at {workdir}")

    depot_tools.ensure()
    cmd = ["gclient", "sync"]
    if shallow:
        cmd.append("--no-history")
    cmd.extend(["-D", "--reset"])
    log("run: " + " ".join(cmd) + f"  (cwd={workdir})")
    subprocess.run(cmd, cwd=str(workdir), check=True, text=True)
