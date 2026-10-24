"""rclone backend — any rclone remote (S3, GCS, R2, B2, Azure, SFTP, WebDAV, local)."""
import json
import shlex
import subprocess

from lib.log import log, die
from backends.base import Backend, BackendContext

GB = 1024 ** 3


def _prefix(config: dict) -> str:
    remote = (config.get("remote") or "").strip()
    path = (config.get("path") or "").strip()
    if not path:
        die("rclone backend requires backend-config.path")
    if remote:
        return f"{remote}:{path}"
    return path


def _excludes(ctx: BackendContext) -> list[str]:
    args: list[str] = []
    for pat in ctx.exclude:
        args.extend(["--exclude", pat])
    return args


def _extra_args(config: dict) -> list[str]:
    extra = config.get("extra_args") or []
    if not isinstance(extra, list):
        die("rclone backend: extra_args must be a list of strings")
    return [str(a) for a in extra]


def _run(cmd: list[str]) -> None:
    log(f"rclone: {' '.join(shlex.quote(c) for c in cmd)}")
    subprocess.run(cmd, check=True, text=True)


class RcloneBackend(Backend):
    def restore(self, ctx: BackendContext) -> bool:
        if self.probe(ctx) <= 0:
            log(f"rclone: miss for {ctx.version}")
            return False
        remote_work = f"{_prefix(ctx.config)}/{ctx.version}"
        ctx.workdir.mkdir(parents=True, exist_ok=True)
        _run([
            "rclone", "sync", remote_work, str(ctx.workdir),
            "--fast-list", "--stats", "30s",
            *_excludes(ctx), *_extra_args(ctx.config),
        ])
        return True

    def save(self, ctx: BackendContext) -> None:
        if not (ctx.workdir / "src" / ".git").exists():
            die(f"rclone: refusing to save — no source at {ctx.workdir}/src/.git")
        remote_work = f"{_prefix(ctx.config)}/{ctx.version}"
        _run([
            "rclone", "sync", str(ctx.workdir), remote_work,
            "--fast-list", "--stats", "30s", "--immutable",
            *_excludes(ctx), *_extra_args(ctx.config),
        ])

    def probe(self, ctx: BackendContext) -> float:
        remote_work = f"{_prefix(ctx.config)}/{ctx.version}"
        result = subprocess.run(
            ["rclone", "size", remote_work, "--json"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return 0.0
        try:
            data = json.loads(result.stdout)
            return float(data.get("bytes", 0)) / GB
        except (json.JSONDecodeError, ValueError):
            return 0.0
