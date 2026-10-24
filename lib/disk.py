"""Filesystem size helpers (portable — os.statvfs works on Linux, Android, macOS)."""
import os
from dataclasses import dataclass

GB = 1024 ** 3


@dataclass
class DiskInfo:
    path: str       # path the caller asked about
    measured: str   # actual path statvfs was run on (nearest existing ancestor)
    free_gb: float
    total_gb: float


def nearest_existing(path: str) -> str:
    """Walk up until we find a path that exists. Filesystem root always exists."""
    p = os.path.abspath(path)
    while not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            return p
        p = parent
    return p


def measure(path: str) -> DiskInfo:
    measured = nearest_existing(path)
    st = os.statvfs(measured)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    return DiskInfo(
        path=path,
        measured=measured,
        free_gb=round(free / GB, 2),
        total_gb=round(total / GB, 2),
  )
