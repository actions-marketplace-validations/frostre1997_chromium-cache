"""GHCR backend — archive-only via oras. Splits into 2 GiB parts, pushes/pulls as OCI artifact."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from lib.log import log, die
from backends.base import Backend, BackendContext

GB = 1024 ** 3
CHUNK_SIZE = 2 * 1024 ** 3
ARTIFACT_TYPE = "application/vnd.frostre.chromium.source.v1"
LAYER_MEDIA_TYPE = "application/zstd"
DEFAULT_REGISTRY = "ghcr.io"
PARTS_GLOB = "chromium.tar.zst.part-*"


def _registry(config: dict) -> str:
    return (config.get("registry") or DEFAULT_REGISTRY).strip()


def _repo(config: dict) -> str:
    r = (config.get("repository") or "").strip()
    if r:
        return r
    env = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not env:
        die("ghcr backend: backend-config.repository missing and GITHUB_REPOSITORY unset")
    return f"{env}-chromium-cache"


def _ref(config: dict, version: str) -> str:
    return f"{_registry(config)}/{_repo(config)}:{version}"


def _token() -> str:
    t = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not t:
        die("ghcr backend: GH_TOKEN or GITHUB_TOKEN must be set")
    return t


def _oras_login(config: dict) -> None:
    actor = os.environ.get("GITHUB_ACTOR", "x-access-token")
    log(f"ghcr: logging in as {actor} to {_registry(config)}")
    subprocess.run(
        ["oras", "login", _registry(config), "-u", actor, "--password-stdin"],
        input=_token(), text=True, check=True,
    )


def _oras_exists(config: dict, version: str) -> bool:
    ref = _ref(config, version)
    r = subprocess.run(
        ["oras", "manifest", "fetch", ref],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def _oras_manifest(config: dict, version: str) -> dict:
    ref = _ref(config, version)
    r = subprocess.run(
        ["oras", "manifest", "fetch", ref],
        capture_output=True, text=True, check=True,
    )
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {}


def _oras_push(config: dict, version: str, files: list[Path], cwd: Path) -> None:
    ref = _ref(config, version)
    args = ["oras", "push", ref, "--artifact-type", ARTIFACT_TYPE]
    for p in files:
        args.append(f"{p.name}:{LAYER_MEDIA_TYPE}")
    log(f"ghcr: push {ref} ({len(files)} part(s))")
    subprocess.run(args, cwd=str(cwd), check=True, text=True)


def _oras_pull(config: dict, version: str, dest: Path) -> None:
    ref = _ref(config, version)
    log(f"ghcr: pull {ref} -> {dest}")
    subprocess.run(
        ["oras", "pull", ref, "-o", str(dest)],
        check=True, text=True,
    )


class GhcrBackend(Backend):
    def restore(self, ctx: BackendContext) -> bool:
        if not _oras_exists(ctx.config, ctx.version):
            log(f"ghcr: miss for {ctx.version}")
            return False
        _oras_login(ctx.config)
        tmp = Path(tempfile.mkdtemp(prefix="ghcr-restore-"))
        try:
            _oras_pull(ctx.config, ctx.version, tmp)
            parts = sorted(tmp.glob(PARTS_GLOB))
            if not parts:
                die(f"ghcr: pulled {_ref(ctx.config, ctx.version)} but no {PARTS_GLOB} found")
            log(f"ghcr: extracting {len(parts)} part(s)")
            self._extract(parts, ctx.workdir)
            return True
        finally:
            subprocess.run(["rm", "-rf", str(tmp)], check=False)

    def save(self, ctx: BackendContext) -> None:
        if not (ctx.workdir / "src" / ".git").exists():
            die(f"ghcr: refusing to save — no source at {ctx.workdir}/src/.git")
        _oras_login(ctx.config)
        tmp = Path(tempfile.mkdtemp(prefix="ghcr-save-"))
        try:
            archive = tmp / "chromium.tar.zst"
            log("ghcr: compressing with zstd -19 -T0")
            self._compress(ctx.workdir, archive)
            log(f"ghcr: splitting into {CHUNK_SIZE}-byte parts")
            self._split(archive, tmp)
            parts = sorted(tmp.glob(PARTS_GLOB))
            _oras_push(ctx.config, ctx.version, parts, tmp)
        finally:
            subprocess.run(["rm", "-rf", str(tmp)], check=False)

    def probe(self, ctx: BackendContext) -> float:
        if not _oras_exists(ctx.config, ctx.version):
            return 0.0
        manifest = _oras_manifest(ctx.config, ctx.version)
        total = 0
        for layer in manifest.get("layers", []):
            try:
                total += int(layer.get("size", 0))
            except (TypeError, ValueError):
                pass
        return total / GB

    # --- internals -------------------------------------------------------

    @staticmethod
    def _compress(workdir: Path, archive: Path) -> None:
        with archive.open("wb") as out:
            tar = subprocess.Popen(
                ["tar", "-C", str(workdir), "-cf", "-", "."],
                stdout=subprocess.PIPE,
            )
            zstd = subprocess.Popen(
                ["zstd", "-19", "-T0", "-q", "-c"],
                stdin=tar.stdout, stdout=out,
            )
            tar.stdout.close()
            zstd.communicate()
            tar.wait()
        if zstd.returncode != 0 or tar.returncode != 0:
            die(f"ghcr: compress failed (tar={tar.returncode} zstd={zstd.returncode})")

    @staticmethod
    def _split(archive: Path, tmp: Path) -> None:
        subprocess.run(
            ["split", "-b", str(CHUNK_SIZE), "-d", "-a", "3",
             str(archive), str(tmp / "chromium.tar.zst.part-")],
            check=True, text=True,
        )
        archive.unlink()

    @staticmethod
    def _extract(parts: list[Path], workdir: Path) -> None:
        workdir.mkdir(parents=True, exist_ok=True)
        cat = subprocess.Popen(
            ["cat", *[str(p) for p in parts]],
            stdout=subprocess.PIPE,
        )
        zstd = subprocess.Popen(
            ["zstd", "-d", "-q", "-c"],
            stdin=cat.stdout, stdout=subprocess.PIPE,
        )
        cat.stdout.close()
        tar = subprocess.Popen(
            ["tar", "-C", str(workdir), "-xf", "-"],
            stdin=zstd.stdout,
            stdout=subprocess.DEVNULL,
        )
        zstd.stdout.close()
        tar.communicate()
        zstd.wait()
        cat.wait()
        if tar.returncode != 0 or zstd.returncode != 0 or cat.returncode != 0:
            die(f"ghcr: extract failed (cat={cat.returncode} zstd={zstd.returncode} tar={tar.returncode})")
