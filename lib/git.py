"""Git command runner."""
import subprocess
from pathlib import Path
from typing import Optional

from lib.log import log


def run(
    args: list[str],
    cwd: Optional[Path] = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    cmd = ["git", *args]
    log("git: " + " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=capture,
    )
