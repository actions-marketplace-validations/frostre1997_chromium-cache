"""Render Markdown to $GITHUB_STEP_SUMMARY."""
import os

from lib.disk import DiskInfo


def _path() -> str | None:
    return os.environ.get("GITHUB_STEP_SUMMARY")


def write(lines: list[str]) -> None:
    p = _path()
    if not p:
        return
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render_plan(
    *,
    mode: str,
    version: str,
    backend: str,
    path: str,
    probe: bool,
    disk: DiskInfo | None = None,
    cache_hit: bool | None = None,
    remote_size_gb: float | None = None,
) -> list[str]:
    lines = [
        "## chromium-cache",
        "",
        f"- Mode: `{mode}`",
        f"- Version: `{version or '(unresolved)'}`",
        f"- Backend: `{backend}`",
        f"- Path: `{path}`",
        f"- Probe-only: `{probe}`",
    ]
    if disk is not None:
        measured = disk.measured if disk.measured != disk.path else "same"
        lines.append(
            f"- Disk: `{disk.free_gb:.2f} / {disk.total_gb:.2f} GB` "
            f"free at `{disk.measured}` (measured for `{measured}`)"
        )
    if cache_hit is not None:
        lines.append(f"- Cache hit: `{'yes' if cache_hit else 'no'}`")
    if remote_size_gb is not None:
        lines.append(f"- Remote size: `{remote_size_gb:.2f} GB`")
    return lines
