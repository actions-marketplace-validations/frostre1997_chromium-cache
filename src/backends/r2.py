"""Cloudflare R2 backend — auto-configured rclone S3 remote.

Reads credentials from backend-config or env vars, sets up the
RCLONE_CONFIG_R2_* environment, then delegates all operations to
RcloneBackend with R2-tuned defaults.
"""
import os

from lib.log import log, die
from backends.base import Backend, BackendContext
from backends.rclone import RcloneBackend

REMOTE = "r2"

_ACCOUNT_ID_VARS = ("CLOUDFLARE_ACCOUNT_ID", "R2_ACCOUNT_ID", "CF_ACCOUNT_ID")
_ACCESS_KEY_VARS = ("CLOUDFLARE_R2_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID", "CF_R2_ACCESS_KEY_ID")
_SECRET_KEY_VARS = ("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY", "CF_R2_SECRET_ACCESS_KEY")


def _first_env(*names: str) -> str | None:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def _configure_rclone(config: dict) -> None:
    """Populate RCLONE_CONFIG_R2_* env vars from config or environment."""
    account_id = (config.get("account_id") or _first_env(*_ACCOUNT_ID_VARS) or "").strip()
    access_key = (config.get("access_key_id") or _first_env(*_ACCESS_KEY_VARS) or "").strip()
    secret_key = (config.get("secret_access_key") or _first_env(*_SECRET_KEY_VARS) or "").strip()

    if not account_id:
        die("r2 backend: account_id missing "
            "(set backend-config.account_id or CLOUDFLARE_ACCOUNT_ID)")
    if not access_key:
        die("r2 backend: access_key_id missing "
            "(set backend-config.access_key_id or CLOUDFLARE_R2_ACCESS_KEY_ID)")
    if not secret_key:
        die("r2 backend: secret_access_key missing "
            "(set backend-config.secret_access_key or CLOUDFLARE_R2_SECRET_ACCESS_KEY)")

    p = f"RCLONE_CONFIG_{REMOTE.upper()}_"
    os.environ[p + "TYPE"] = "s3"
    os.environ[p + "PROVIDER"] = "Cloudflare"
    os.environ[p + "ACCESS_KEY_ID"] = access_key
    os.environ[p + "SECRET_ACCESS_KEY"] = secret_key
    os.environ[p + "ENDPOINT"] = f"https://{account_id}.r2.cloudflarestorage.com"
    os.environ[p + "ACL"] = "private"


def _r2_config(config: dict) -> dict:
    bucket = (config.get("bucket") or "").strip().strip("/")
    if not bucket:
        die("r2 backend: backend-config.bucket is required")
    prefix = (config.get("prefix") or "chromium").strip().strip("/")
    path = f"{bucket}/{prefix}" if prefix else bucket

    user_extra = config.get("extra_args") or []
    if not isinstance(user_extra, list):
        die("r2 backend: extra_args must be a list of strings")

    tuning = [
        "--transfers", str(config.get("transfers", 32)),
        "--checkers", str(config.get("checkers", 32)),
        "--s3-chunk-size", str(config.get("chunk_size", "16M")),
        "--s3-no-check-bucket",
    ]
    return {
        "remote": REMOTE,
        "path": path,
        "extra_args": tuning + [str(a) for a in user_extra],
    }


class R2Backend(Backend):
    """Cloudflare R2 — delegates to RcloneBackend with auto-configured remote."""

    def _wrap(self, ctx: BackendContext) -> BackendContext:
        _configure_rclone(ctx.config)
        return BackendContext(
            version=ctx.version,
            workdir=ctx.workdir,
            src_path=ctx.src_path,
            config=_r2_config(ctx.config),
            exclude=ctx.exclude,
            shallow=ctx.shallow,
        )

    def restore(self, ctx: BackendContext) -> bool:
        return RcloneBackend().restore(self._wrap(ctx))

    def save(self, ctx: BackendContext) -> None:
        return RcloneBackend().save(self._wrap(ctx))

    def probe(self, ctx: BackendContext) -> float:
        return RcloneBackend().probe(self._wrap(ctx))
