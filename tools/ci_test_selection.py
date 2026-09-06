from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


DEFAULT_POLICY = ".github/python-test-selection.json"
SUPPORTED_POLICY_VERSION = 1
CONFIG_ERROR_EXIT = 2


class SelectionError(ValueError):
    pass


@dataclass(frozen=True)
class Exclusion:
    path: str
    ci_job: str
    command: str
    reason: str


@dataclass(frozen=True)
class SelectionPolicy:
    version: int
    roots: tuple[str, ...]
    pattern: str
    exclusions: tuple[Exclusion, ...]


@dataclass(frozen=True)
class TestSelection:
    discovered: tuple[str, ...]
    selected: tuple[str, ...]
    excluded: tuple[Exclusion, ...]


def _require_nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SelectionError(f"{field} must be a non-empty string")
    return value


def _normalized_repo_path(value: object, field: str) -> str:
    text = _require_nonempty_string(value, field)
    path = PurePosixPath(text)
    if path.is_absolute() or text != path.as_posix() or ".." in path.parts or "." in path.parts:
        raise SelectionError(f"{field} must be a normalized repository-relative POSIX path: {text!r}")
    return text


def load_policy(path: Path) -> SelectionPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SelectionError(f"cannot read test-selection policy {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise SelectionError("test-selection policy must be a JSON object")
    if raw.get("version") != SUPPORTED_POLICY_VERSION:
        raise SelectionError(
            f"unsupported test-selection policy version {raw.get('version')!r}; "
            f"expected {SUPPORTED_POLICY_VERSION}"
        )

    roots_raw = raw.get("roots")
    if not isinstance(roots_raw, list) or not roots_raw:
        raise SelectionError("roots must be a non-empty array")
    roots = tuple(_normalized_repo_path(item, "roots[]") for item in roots_raw)
    if list(roots) != sorted(set(roots)):
        raise SelectionError("roots must be unique and sorted")

    pattern = _require_nonempty_string(raw.get("pattern"), "pattern")

    exclusions_raw = raw.get("exclusions")
    if not isinstance(exclusions_raw, list):
        raise SelectionError("exclusions must be an array")
    exclusions: list[Exclusion] = []
    for index, item in enumerate(exclusions_raw):
        if not isinstance(item, dict):
            raise SelectionError(f"exclusions[{index}] must be an object")
        expected = {"path", "ciJob", "command", "reason"}
        if set(item) != expected:
            raise SelectionError(
                f"exclusions[{index}] must contain exactly {sorted(expected)}"
            )
        exclusions.append(
            Exclusion(
                path=_normalized_repo_path(item["path"], f"exclusions[{index}].path"),
                ci_job=_require_nonempty_string(item["ciJob"], f"exclusions[{index}].ciJob"),
                command=_require_nonempty_string(item["command"], f"exclusions[{index}].command"),
                reason=_require_nonempty_string(item["reason"], f"exclusions[{index}].reason"),
            )
        )

    exclusion_paths = [item.path for item in exclusions]
    if exclusion_paths != sorted(set(exclusion_paths)):
        raise SelectionError("exclusions must have unique paths in deterministic sorted order")

    return SelectionPolicy(
        version=SUPPORTED_POLICY_VERSION,
        roots=roots,
        pattern=pattern,
        exclusions=tuple(exclusions),
    )


def tracked_files(repo_root: Path) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise SelectionError(f"cannot enumerate committed files with git ls-files: {detail}") from exc
    return tuple(sorted(item for item in completed.stdout.decode("utf-8").split("\0") if item))


def _under_root(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def discover_tests(files: Iterable[str], policy: SelectionPolicy) -> tuple[str, ...]:
    discovered = {
        path
        for path in files
        if any(_under_root(path, root) for root in policy.roots)
        and fnmatch.fnmatch(PurePosixPath(path).name, policy.pattern)
        and PurePosixPath(path).suffix == ".py"
    }
    return tuple(sorted(discovered))


def select_tests(files: Iterable[str], policy: SelectionPolicy) -> TestSelection:
    discovered = discover_tests(files, policy)
    discovered_set = set(discovered)
    excluded_paths = {item.path for item in policy.exclusions}

    stale = sorted(excluded_paths - discovered_set)
    if stale:
        raise SelectionError(
            "excluded test paths are not committed discovered test modules: " + ", ".join(stale)
        )

    for item in policy.exclusions:
        if item.path not in item.command:
            raise SelectionError(
                f"exclusion command for {item.path} must name the excluded test path explicitly"
            )

    selected = tuple(path for path in discovered if path not in excluded_paths)
    if not selected:
        raise SelectionError("test selection is empty")

    return TestSelection(
        discovered=discovered,
        selected=selected,
        excluded=policy.exclusions,
    )


def repository_selection(repo_root: Path, policy_path: Path) -> TestSelection:
    policy = load_policy(policy_path)
    return select_tests(tracked_files(repo_root), policy)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic committed Python test selection")
    parser.add_argument("command", choices=("validate", "list", "run"))
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = repo_root / policy_path

    try:
        selection = repository_selection(repo_root, policy_path)
    except SelectionError as exc:
        print(f"test-selection: {exc}", file=sys.stderr)
        return CONFIG_ERROR_EXIT

    if args.command == "validate":
        print(
            f"python tests: {len(selection.discovered)} discovered, "
            f"{len(selection.selected)} selected, {len(selection.excluded)} specialized exclusions"
        )
        return 0

    if args.command == "list":
        for path in selection.selected:
            print(path)
        return 0

    completed = subprocess.run(
        [sys.executable, "-m", "unittest", *selection.selected],
        cwd=repo_root,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
