"""Write to $GITHUB_OUTPUT."""
import os
from pathlib import Path


def _path() -> Path | None:
    p = os.environ.get("GITHUB_OUTPUT")
    return Path(p) if p else None


def write(**kwargs) -> None:
    p = _path()
    if p is None:
        return
    lines = [f"{k}={v}" for k, v in kwargs.items()]
    with p.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
