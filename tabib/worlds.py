"""Loading a world package: resolve, check the versions, verify, import.

    world = load_world("hospital-world")

A package is a directory with a manifest, a module and its content. It is data
that happens to carry a little code, and the point of that is reproducibility: a
number measured in 2026 is re-measurable in 2027 by loading the same package
version against the same engine version, both of which ride on every record.

The manifest may name the science served on the world, under `[world]
scenario`: a bare name is a module in `scenarios/`, a path ending in `.py` is a
file inside the package itself. That key is what lets one directory carry both
halves; a package without it still loads, and `tabib.load` is the only caller
that needs it.

Nothing is fetched here. Packages are resolved from disk or from the local
cache, because the compute nodes are offline and a world that had to be downloaded at
run time would be a world that cannot be built where it is served. A missing
package is an error at load, never a silently empty world.
"""

from __future__ import annotations

import hashlib
import importlib.util
import tomllib
from pathlib import Path

from . import engine
from .hub import cache_path

ROOT = Path(__file__).resolve().parents[1] / "worlds"


class WorldError(ValueError):
    pass


def _fits(constraint: str, version: str) -> bool:
    """`>=0.1,<0.2` against `0.1.0`, on the two leading numbers.

    Written out rather than imported: it is eight lines against a packaging
    dependency paid on every machine that runs the instrument, and the engine's
    own versioning is the only thing it ever compares.
    """
    def key(v: str) -> tuple:
        return tuple(int(p) for p in v.split(".")[:2] if p.isdigit())

    got = key(version)
    for clause in (c.strip() for c in constraint.split(",") if c.strip()):
        op = "".join(c for c in clause if not c.isdigit() and c != ".")
        want = key(clause[len(op):])
        if op not in (">=", "<", "==") or not want:
            # a constraint nobody can read is not a satisfied constraint. The
            # first version fell through to True, so a typo in a manifest served
            # a world against an engine it was never written for
            raise WorldError(
                f"cannot read the engine constraint {constraint!r} at {clause!r}: "
                "a version rule that is not understood is refused, never assumed")
        if op == ">=" and not got >= want:
            return False
        if op == "<" and not got < want:
            return False
        if op == "==" and got != want:
            return False
    return True


def resolve(ref: str, root: Path | None = None) -> Path:
    """A package reference to a directory.

    A bare name comes from `worlds/`. `owner/name` is the form a published
    package carries: it is served from `worlds/` when the name is there, and
    from the local cache otherwise. Publishing is a disclosure decision, not a
    loading one, and the two should not be entangled in the code that reads a
    manifest.
    """
    if ("/" in ref or "\\" in ref) and Path(ref).is_dir():
        return Path(ref)
    # a bare name is always a package name, never a directory that happens to
    # share it: `load_world("worlds")` from the wrong cwd used to resolve to
    # whatever was lying there
    local = (root or ROOT) / ref.split("/")[-1]
    if "/" in ref and not local.is_dir() and cache_path(ref).is_dir():
        return cache_path(ref)
    return local


def load_world(ref: str, root: Path | None = None):
    """The package's module, with its manifest attached as `MANIFEST`.

    Verifies every content hash the manifest declares. A world whose content has
    moved under it is not the world whose numbers were published, and finding
    that out at load is the whole reason the hashes are there.
    """
    path = resolve(ref, root)
    manifest_at = path / "manifest.toml"
    if not manifest_at.is_file():
        raise WorldError(f"no world package at {path}: expected a manifest.toml")
    manifest = tomllib.loads(manifest_at.read_text(encoding="utf-8"))
    spec = manifest.get("world", {})

    need = spec.get("engine", "")
    if need and not _fits(need, engine.VERSION):
        raise WorldError(
            f"{spec.get('name', ref)} needs engine {need}, this is "
            f"{engine.VERSION}: a world served by an engine it was not written "
            "against is a different instrument")

    for name, want in (manifest.get("content") or {}).items():
        blob = path / "content" / name
        if not blob.is_file():
            raise WorldError(f"{spec.get('name', ref)}: {name} is missing")
        got = "sha256:" + hashlib.sha256(blob.read_bytes()).hexdigest()
        if got != want:
            raise WorldError(
                f"{spec.get('name', ref)}: {name} is not the file this package "
                f"declares.\n  declared {want}\n  found    {got}")

    module = _import(path / "world.py", spec.get("name", path.name))
    module.MANIFEST = manifest
    module.VERSION = f"{spec.get('name', path.name)}/{spec.get('version', '0')}"
    module.PATH = path
    return module


def _import(at: Path, name: str):
    spec = importlib.util.spec_from_file_location(f"worlds.{name}", at)
    if spec is None or spec.loader is None:
        raise WorldError(f"cannot import {at}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> dict[str, str]:
    """The hashes a manifest should declare, for whoever regenerates content."""
    return {p.name: "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((path / "content").glob("*.json"))}
