from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable

from tools.roadmap import validate_repository as validate_roadmap


ROOT = Path(__file__).resolve().parents[1]
TODO = ROOT / "TODO.md"
POLICY = ROOT / "backlog" / "policy-and-execution.md"
M9_M10 = ROOT / "backlog" / "m9-m10-release-conformance.md"

TODO_AUTHORITY = (
    "`roadmap/v1/` is the sole machine-readable authority for migrated milestone IDs, "
    "order, priority, status, dependencies, and terminal disposition."
)
POLICY_AUTHORITY = (
    "`roadmap/v1/` is the sole machine-readable roadmap authority for explicitly migrated milestones."
)
CONFORMANCE_AUTHORITY = (
    "`spec/conformance-manifest.json` is the separate authoritative versioned "
    "implementation/support source."
)
CHANNEL_AUTHORITY = "Operational execution state remains on `agents/channel`"
PROJECT_AI_FREE = "The project tree is intentionally `.ai/**`-free."
M9_08_BLOCKED = "actual tag creation and public publication remain externally blocked"


def _is_ai_path(path: str) -> bool:
    return path == ".ai" or path.startswith(".ai/")


def tracked_paths(root: Path = ROOT) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return tuple(
        field.decode("utf-8", "surrogateescape")
        for field in completed.stdout.split(b"\0")
        if field
    )


def violations(
    root: Path = ROOT,
    *,
    paths: Iterable[str] | None = None,
) -> tuple[str, ...]:
    errors: list[str] = []
    project_paths = tuple(paths) if paths is not None else tracked_paths(root)
    ai_paths = sorted(path for path in project_paths if _is_ai_path(path))
    if ai_paths:
        errors.append("project must not track .ai/** paths: " + ", ".join(ai_paths))

    todo = (root / "TODO.md").read_text(encoding="utf-8")
    policy = (root / "backlog" / "policy-and-execution.md").read_text(encoding="utf-8")
    m9_m10 = (root / "backlog" / "m9-m10-release-conformance.md").read_text(
        encoding="utf-8"
    )

    required_markers = (
        ("TODO.md roadmap authority", TODO_AUTHORITY, todo),
        ("policy roadmap authority", POLICY_AUTHORITY, policy),
        ("conformance authority", CONFORMANCE_AUTHORITY, policy),
        ("channel operational authority", CHANNEL_AUTHORITY, policy),
        ("project .ai-free invariant", PROJECT_AI_FREE, policy),
        ("M9-08 external publication state", M9_08_BLOCKED, m9_m10),
    )
    for label, marker, text in required_markers:
        if marker not in text:
            errors.append(f"missing {label} marker")

    if "- [x] **P1** **M9-08** Publish the first explicitly scoped toolchain pre-release" in m9_m10:
        errors.append("M9-08 must not be marked complete before public publication exists")

    for error in validate_roadmap(root):
        errors.append(f"{error['code']} {error['subject']}: {error['message']}")

    return tuple(errors)


def main() -> int:
    try:
        errors = violations()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"repository state validation failed to run: {exc}", file=sys.stderr)
        return 2

    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
