"""Compiler-owned workspace discovery and isolated multi-root snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

from tools.aidl_parser import iter_aidl_files
from tools.compiler_snapshot import CompilerSnapshot, create_compiler_snapshot


def _normalize(path: Path) -> Path:
    return path.absolute().resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _root_sort_key(root: Path) -> tuple[str, ...]:
    return tuple(root.parts)


@dataclass(frozen=True)
class CompilerWorkspace:
    """Deterministic roots, ownership, and one isolated compiler snapshot per root."""

    roots: tuple[Path, ...]
    ownership: Mapping[Path, Path]
    snapshots: Mapping[Path, CompilerSnapshot]

    def owner(self, source_path: Path) -> Path | None:
        return self.ownership.get(_normalize(source_path))

    def snapshot_for(self, source_path: Path) -> CompilerSnapshot | None:
        root = self.owner(source_path)
        return self.snapshots.get(root) if root is not None else None

    def text(self, source_path: Path) -> str:
        snapshot = self.snapshot_for(source_path)
        if snapshot is None:
            raise ValueError(f"source is not owned by workspace: {source_path}")
        return snapshot.text(source_path)


def discover_workspace_roots(paths: Iterable[Path]) -> tuple[Path, ...]:
    """Normalize, de-duplicate, and deterministically order configured roots."""

    return tuple(sorted({_normalize(path) for path in paths}, key=_root_sort_key))


def owner_for_path(source_path: Path, roots: Iterable[Path]) -> Path | None:
    """Assign a path to the most-specific configured root deterministically."""

    normalized = _normalize(source_path)
    candidates = [root for root in roots if _is_within(normalized, root)]
    if not candidates:
        return None
    candidates.sort(key=lambda root: (-len(root.parts), _root_sort_key(root)))
    return candidates[0]


def create_compiler_workspace(
    paths: Iterable[Path],
    overrides: Mapping[Path, str] | None = None,
) -> CompilerWorkspace:
    """Build isolated snapshots for one or more roots.

    Saved files are discovered recursively, then assigned to exactly one root using
    most-specific-root ownership. Explicit unsaved overrides may replace owned saved
    files or admit a new ``.aidl`` file underneath exactly one configured root. Files
    outside all roots and non-AIDL unsaved files are rejected.
    """

    roots = discover_workspace_roots(paths)
    if not roots:
        raise ValueError("workspace requires at least one root")

    normalized_overrides = {_normalize(path): text for path, text in (overrides or {}).items()}
    for path in normalized_overrides:
        if path.suffix != ".aidl":
            raise ValueError(f"workspace override must be an .aidl file: {path}")
        if owner_for_path(path, roots) is None:
            raise ValueError(f"workspace override is outside configured roots: {path}")

    saved: set[Path] = set()
    for root in roots:
        saved.update(_normalize(path) for path in iter_aidl_files([root]))

    all_paths = saved | set(normalized_overrides)
    ownership: dict[Path, Path] = {}
    for path in sorted(all_paths, key=str):
        owner = owner_for_path(path, roots)
        if owner is None:
            continue
        ownership[path] = owner

    snapshots: dict[Path, CompilerSnapshot] = {}
    for root in roots:
        owned_paths = tuple(path for path, owner in ownership.items() if owner == root)
        root_overrides = {
            path: normalized_overrides[path]
            for path in owned_paths
            if path in normalized_overrides
        }
        snapshots[root] = create_compiler_snapshot(
            [root],
            root_overrides,
            include_paths=owned_paths,
        )

    return CompilerWorkspace(
        roots=roots,
        ownership=MappingProxyType(ownership),
        snapshots=MappingProxyType(snapshots),
    )
