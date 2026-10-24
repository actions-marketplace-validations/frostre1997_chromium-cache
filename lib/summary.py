"""Render Markdown to $GITHUB_STEP_SUMMARY."""
import os


def _path() -> str | None:
    return os.environ.get("GITHUB_STEP_SUMMARY")


def write(lines: list[str]) -> None:
    p = _path()
    if not p:
        return
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def render_plan(*, mode: str, version: str, backend: str,
                path: str, probe: bool) -> list[str]:
    return [
        "## chromium-cache",
        "",
        f"- Mode: `{mode}`",
        f"- Version: `{version or '(unresolved)'}`",
        f"- Backend: `{backend}`",
        f"- Path: `{path}`",
        f"- Probe-only: `{probe}`",
    ]
