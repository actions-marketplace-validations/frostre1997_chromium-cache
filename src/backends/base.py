"""Backend ABC shared by all storage implementations."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BackendContext:
    version: str
    workdir: Path          # e.g. /workspace/chromium
    src_path: Path         # workdir / "src"
    config: dict = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    shallow: bool = True


class Backend(ABC):
    """Storage backend interface. One instance per action invocation."""

    @abstractmethod
    def restore(self, ctx: BackendContext) -> bool:
        """Return True on cache hit (tree now present at ctx.workdir), False on miss."""

    @abstractmethod
    def save(self, ctx: BackendContext) -> None:
        """Persist ctx.workdir to the backend under ctx.version."""

    @abstractmethod
    def probe(self, ctx: BackendContext) -> float:
        """Return size in GB currently stored for ctx.version (0.0 on miss)."""
