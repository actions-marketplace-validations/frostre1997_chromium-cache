"""Structured logging to stderr with GitHub Actions annotations."""
import sys


PREFIX = "[chromium-cache]"


def log(msg: str) -> None:
    print(f"{PREFIX} {msg}", file=sys.stderr, flush=True)


def warn(msg: str) -> None:
    print(f"::warning::{PREFIX} {msg}", file=sys.stderr, flush=True)


def error(msg: str) -> None:
    print(f"::error::{PREFIX} {msg}", file=sys.stderr, flush=True)


def die(msg: str, code: int = 1):
    error(msg)
    sys.exit(code)
