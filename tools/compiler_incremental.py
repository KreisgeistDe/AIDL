"""Compiler-owned incremental workspace analysis and deterministic invalidation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping

from tools.aidl_parser import iter_aidl_files
from tools.compiler_snapshot import CompilerSnapshot, create_compiler_snapshot
from tools.compiler_workspace import discover_workspace_roots, owner_for_path


def _normalize(path: Path) -> Path:
    return path.absolute().resolve(strict=False)


class CompilerCancelled(RuntimeError):
    """Raised when a caller cancels semantic work before it can be published."""


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def check(self) -> None:
        if self._cancelled:
            raise CompilerCancelled("compiler analysis cancelled")


@dataclass(frozen=True)
class IncrementalStats:
    hits: int
    misses: int
    invalidations: int
    builds: int


@dataclass(frozen=True)
class _CacheEntry:
    fingerprint: str
    snapshot: CompilerSnapshot


class IncrementalCompilerState:
    """Per-root immutable snapshot cache keyed by exact owned source bytes.

    The cache never shares semantic state across workspace roots. Any owned source
    change invalidates the whole owning root, conservatively covering transitive
    semantic dependencies while preserving deterministic behavior.
    """

    def __init__(self, roots: Iterable[Path]):
        self.roots = discover_workspace_roots(roots)
        if not self.roots:
            raise ValueError("incremental compiler state requires at least one root")
        self._overrides: dict[Path, str] = {}
        self._cache: dict[Path, _CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        self._builds = 0

    @property
    def overrides(self) -> Mapping[Path, str]:
        return dict(self._overrides)

    @property
    def stats(self) -> IncrementalStats:
        return IncrementalStats(self._hits, self._misses, self._invalidations, self._builds)

    def owner(self, source_path: Path) -> Path | None:
        return owner_for_path(_normalize(source_path), self.roots)

    def set_override(self, source_path: Path, text: str) -> None:
        path = _normalize(source_path)
        if path.suffix != ".aidl":
            raise ValueError(f"workspace override must be an .aidl file: {path}")
        owner = self.owner(path)
        if owner is None:
            raise ValueError(f"workspace override is outside configured roots: {path}")
        if self._overrides.get(path) == text:
            return
        self._overrides[path] = text
        self.invalidate_root(owner)

    def clear_override(self, source_path: Path) -> None:
        path = _normalize(source_path)
        if path not in self._overrides:
            return
        owner = self.owner(path)
        del self._overrides[path]
        if owner is not None:
            self.invalidate_root(owner)

    def invalidate_root(self, root: Path) -> None:
        normalized = _normalize(root)
        if normalized in self._cache:
            del self._cache[normalized]
        self._invalidations += 1

    def invalidate_paths(self, paths: Iterable[Path]) -> tuple[Path, ...]:
        affected = sorted(
            {owner for path in paths if (owner := self.owner(path)) is not None},
            key=str,
        )
        for root in affected:
            self.invalidate_root(root)
        return tuple(affected)

    def _owned_paths(self, root: Path) -> tuple[Path, ...]:
        saved: set[Path] = set()
        for configured_root in self.roots:
            saved.update(_normalize(path) for path in iter_aidl_files([configured_root]))
        candidates = saved | set(self._overrides)
        return tuple(
            path
            for path in sorted(candidates, key=str)
            if owner_for_path(path, self.roots) == root
        )

    def _fingerprint(self, root: Path, paths: tuple[Path, ...], token: CancellationToken | None) -> str:
        digest = sha256()
        digest.update(b"aidl-incremental-v1\0")
        digest.update(str(root).encode("utf-8"))
        digest.update(b"\0")
        for path in paths:
            if token is not None:
                token.check()
            text = self._overrides.get(path)
            if text is None:
                if not path.exists():
                    continue
                text = path.read_text(encoding="utf-8")
            digest.update(str(path).encode("utf-8"))
            digest.update(b"\0")
            digest.update(text.encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    def snapshot_for(self, source_path: Path, token: CancellationToken | None = None) -> CompilerSnapshot | None:
        path = _normalize(source_path)
        root = self.owner(path)
        if root is None:
            return None
        return self.snapshot_for_root(root, token)

    def snapshot_for_root(self, root: Path, token: CancellationToken | None = None) -> CompilerSnapshot:
        normalized_root = _normalize(root)
        if normalized_root not in self.roots:
            raise ValueError(f"root is not configured: {root}")
        if token is not None:
            token.check()
        paths = self._owned_paths(normalized_root)
        fingerprint = self._fingerprint(normalized_root, paths, token)
        cached = self._cache.get(normalized_root)
        if cached is not None and cached.fingerprint == fingerprint:
            self._hits += 1
            return cached.snapshot
        self._misses += 1
        root_overrides = {path: self._overrides[path] for path in paths if path in self._overrides}
        snapshot = create_compiler_snapshot(
            [normalized_root],
            root_overrides,
            include_paths=paths,
        )
        if token is not None:
            token.check()
        self._builds += 1
        self._cache[normalized_root] = _CacheEntry(fingerprint=fingerprint, snapshot=snapshot)
        return snapshot
