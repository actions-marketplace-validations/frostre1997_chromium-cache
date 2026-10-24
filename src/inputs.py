"""Parse and validate composite-action inputs from env."""
from dataclasses import dataclass, field
import json
import os

from lib.log import die


VALID_MODES = {"restore", "save", "both"}
VALID_BACKENDS = {"rclone", "ghcr", "local"}


def _str(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    die(f"input {name} must be boolean (got {v!r})")


def _int(name: str, default: int) -> int:
    v = os.environ.get(name, "").strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        die(f"input {name} must be an integer (got {v!r})")


def _json(name: str, default: dict) -> dict:
    v = os.environ.get(name, "").strip()
    if not v:
        return dict(default)
    try:
        parsed = json.loads(v)
    except json.JSONDecodeError as e:
        die(f"input {name} must be valid JSON: {e}")
    if not isinstance(parsed, dict):
        die(f"input {name} must be a JSON object (got {type(parsed).__name__})")
    return parsed


@dataclass
class Inputs:
    mode: str
    version: str
    path: str
    backend: str
    backend_config: dict = field(default_factory=dict)
    force_save: bool = False
    min_free_gb: int = 30
    exclude: list[str] = field(default_factory=list)
    shallow: bool = True
    probe_only: bool = False


def _resolve_path(raw: str) -> str:
    if not raw:
        ws = os.environ.get("GITHUB_WORKSPACE")
        if not ws:
            die("input path is empty and GITHUB_WORKSPACE is not set")
        return f"{ws}/chromium"
    if not raw.startswith("/"):
        ws = os.environ.get("GITHUB_WORKSPACE")
        if not ws:
            die("input path is relative and GITHUB_WORKSPACE is not set")
        return f"{ws}/{raw}"
    return raw


def parse() -> Inputs:
    mode = _str("INPUT_MODE", "both").strip().lower()
    if mode not in VALID_MODES:
        die(f"mode must be one of {sorted(VALID_MODES)} (got {mode!r})")

    backend = _str("INPUT_BACKEND", "ghcr").strip().lower()
    if backend not in VALID_BACKENDS:
        die(f"backend must be one of {sorted(VALID_BACKENDS)} (got {backend!r})")

    min_free_gb = _int("INPUT_MIN_FREE_GB", 30)
    if min_free_gb < 0:
        die(f"min-free-gb must be >= 0 (got {min_free_gb})")

    exclude_raw = _str("INPUT_EXCLUDE").strip()
    exclude = [p.strip() for p in exclude_raw.split(",") if p.strip()]

    return Inputs(
        mode=mode,
        version=_str("INPUT_VERSION").strip(),
        path=_resolve_path(_str("INPUT_PATH").strip()),
        backend=backend,
        backend_config=_json("INPUT_BACKEND_CONFIG", {}),
        force_save=_bool("INPUT_FORCE_SAVE", False),
        min_free_gb=min_free_gb,
        exclude=exclude,
        shallow=_bool("INPUT_SHALLOW", True),
        probe_only=_bool("INPUT_PROBE_ONLY", False),
    )
