"""Pre-flight disk assertion."""
import sys

from lib.log import log, error
from lib.disk import DiskInfo, measure


def check(min_free_gb: int, path: str, probe_only: bool) -> DiskInfo | None:
    """
    Returns DiskInfo on measurement, None if skipped.
    Dies (exit 1) if measured free space is below min_free_gb.
    """
    if probe_only:
        log("disk check: skipped (probe-only)")
        return None

    if min_free_gb <= 0:
        log("disk check: skipped (min-free-gb=0)")
        return None

    info = measure(path)
    log(
        f"disk: free={info.free_gb:.2f} GB total={info.total_gb:.2f} GB "
        f"at {info.measured}"
        + ("" if info.measured == info.path else f" (for {info.path})")
    )

    if min_free_gb > info.total_gb:
        error(
            f"insufficient disk: min-free-gb={min_free_gb} exceeds total "
            f"volume size {info.total_gb:.2f} GB at {info.measured}"
        )
        error("  hints:")
        error("    - use a larger runner (ubuntu-latest-16-cores has ~180 GB)")
        error("    - run frostre1997/cleanser before this action to reclaim space")
        error("    - set min-free-gb: 0 to skip this check entirely")
        sys.exit(1)

    if info.free_gb < min_free_gb:
        error(
            f"insufficient disk: need >= {min_free_gb} GB free, "
            f"have {info.free_gb:.2f} GB (total {info.total_gb:.2f} GB) "
            f"at {info.measured}"
        )
        error("  hints:")
        error("    - run frostre1997/cleanser before this action to reclaim space")
        error("    - use a larger runner (ubuntu-latest-16-cores has ~180 GB)")
        error("    - narrow the build target (component build, v8-only, etc.)")
        error("    - set min-free-gb: 0 to skip this check entirely")
        sys.exit(1)

    return info
