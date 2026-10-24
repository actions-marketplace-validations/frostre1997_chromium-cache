#!/usr/bin/env python3
"""chromium-cache entry point (M2)."""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
sys.path.insert(0, str(_here.parent))            # src/
sys.path.insert(0, str(_here.parent.parent))     # repo root

from lib.log import log                          # noqa: E402
from lib import summary                          # noqa: E402
import inputs                                    # noqa: E402
import outputs                                   # noqa: E402
import disk_guard                                # noqa: E402


def resolve_version(inp) -> str:
    """M2: no network. Echo the pinned version, or empty placeholder."""
    return inp.version


def main() -> int:
    inp = inputs.parse()

    # M2: fail fast BEFORE any network/backend work
    disk = disk_guard.check(inp.min_free_gb, inp.path, inp.probe_only)

    version = resolve_version(inp)
    src_path = f"{inp.path}/src"

    log(
        f"plan: mode={inp.mode} version={version or '(unresolved)'} "
        f"backend={inp.backend} path={inp.path} probe={inp.probe_only}"
    )
    log(
        f"cfg_keys={sorted(inp.backend_config)} "
        f"min_free_gb={inp.min_free_gb} shallow={inp.shallow} "
        f"exclude={inp.exclude or '(none)'}"
    )

    outputs.write(**{
        "cache-hit": "false",
        "path": src_path,
        "version": version,
        "remote-size-gb": "0",
    })

    summary.write(summary.render_plan(
        mode=inp.mode,
        version=version,
        backend=inp.backend,
        path=src_path,
        probe=inp.probe_only,
        disk=disk,
    ))

    log("M2 stub complete — disk check enforced, no backend operations performed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
