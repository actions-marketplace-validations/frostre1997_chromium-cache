#!/usr/bin/env python3
"""chromium-cache entry point (M3)."""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
sys.path.insert(0, str(_here.parent))            # src/
sys.path.insert(0, str(_here.parent.parent))     # repo root

from lib.log import log, die                     # noqa: E402
from lib import summary                          # noqa: E402
import inputs                                    # noqa: E402
import outputs                                   # noqa: E402
import disk_guard                                # noqa: E402
import version as version_mod                    # noqa: E402
import fetch                                     # noqa: E402
import gclient                                   # noqa: E402
from backends.base import Backend, BackendContext  # noqa: E402


def _make_backend(name: str) -> Backend:
    if name == "local":
        from backends.local import LocalBackend
        return LocalBackend()
    if name == "rclone":
        from backends.rclone import RcloneBackend
        return RcloneBackend()
    die(f"backend {name!r} not implemented yet (ghcr lands in M6)")


def main() -> int:
    inp = inputs.parse()
    disk = disk_guard.check(inp.min_free_gb, inp.path, inp.probe_only)

    version = version_mod.resolve(inp.version)
    log(f"version: resolved {version}")

    ctx = BackendContext(
        version=version,
        workdir=Path(inp.path),
        src_path=Path(inp.path) / "src",
        config=inp.backend_config,
        exclude=inp.exclude,
        shallow=inp.shallow,
    )
    backend = _make_backend(inp.backend)

    cache_hit = False
    remote_size = 0.0

    if inp.probe_only:
        remote_size = backend.probe(ctx)
        log(f"probe: version={version} present={remote_size > 0} size={remote_size:.2f} GB")
    elif inp.mode in ("restore", "both"):
        cache_hit = backend.restore(ctx)
        log(f"restore: {'hit' if cache_hit else 'miss'} (version={version})")
        fetch.ensure_at_version(ctx.workdir, version, inp.shallow)
        gclient.sync(ctx.workdir, inp.shallow)
        log("fetch+gclient: complete")

    if inp.mode in ("save", "both") and not inp.probe_only:
        if cache_hit and not inp.force_save:
            log("save: skipped (cache-hit and force-save=false)")
        else:
            backend.save(ctx)
            remote_size = backend.probe(ctx)
            log(f"save: complete ({remote_size:.2f} GB in cache)")

    outputs.write(**{
        "cache-hit": "true" if cache_hit else "false",
        "path": str(ctx.src_path),
        "version": version,
        "remote-size-gb": f"{remote_size:.2f}",
    })

    summary.write(summary.render_plan(
        mode=inp.mode,
        version=version,
        backend=inp.backend,
        path=str(ctx.src_path),
        probe=inp.probe_only,
        disk=disk,
        cache_hit=cache_hit if inp.mode in ("restore", "both") and not inp.probe_only else None,
        remote_size_gb=remote_size,
    ))

    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
