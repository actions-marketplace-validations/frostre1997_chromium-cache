"""Chromium version resolution + validation."""
import json
import re
import urllib.request

from lib.log import log, die


CHROMIUM_DASH_URL = (
    "https://chromiumdash.appspot.com/fetch_releases"
    "?channel=Stable&platform=Linux&num=1"
)

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


def is_valid(version: str) -> bool:
    return bool(VERSION_RE.match(version))


def get_latest_stable(timeout: float = 10.0) -> str:
    log(f"version: resolving latest stable from Chromium Dash")
    req = urllib.request.Request(
        CHROMIUM_DASH_URL,
        headers={"User-Agent": "chromium-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        die(f"version: could not reach Chromium Dash: {e}")

    if not isinstance(data, list) or not data:
        die("version: Chromium Dash returned unexpected payload")

    v = data[0].get("version", "")
    if not is_valid(v):
        die(f"version: Chromium Dash returned invalid version {v!r}")
    return v


def resolve(requested: str) -> str:
    """Empty input → latest stable. Otherwise validate and return."""
    if not requested:
        return get_latest_stable()
    if not is_valid(requested):
        die(
            f"version: {requested!r} is not a valid Chromium version "
            f"(expected N.N.N.N, e.g. 131.0.6778.85)"
        )
    return requested
