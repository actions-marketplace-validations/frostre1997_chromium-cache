"""depot_tools management — clone on demand, put on PATH."""
import os
from pathlib import Path

from lib.log import log
from lib import git


URL = "https://chromium.googlesource.com/chromium/tools/depot_tools.git"


def path() -> Path:
    return Path(os.environ.get("DEPOT_TOOLS", str(Path.home() / "depot_tools")))


def ensure() -> Path:
    """Clone depot_tools if missing and prepend to PATH. Idempotent."""
    p = path()
    if not (p / "fetch").exists():
        log(f"depot_tools: cloning into {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        git.run(["clone", "--depth", "1", URL, str(p)])
    else:
        log(f"depot_tools: using {p}")
    current = os.environ.get("PATH", "")
    if str(p) not in current.split(os.pathsep):
        os.environ["PATH"] = f"{p}{os.pathsep}{current}"
    return p
