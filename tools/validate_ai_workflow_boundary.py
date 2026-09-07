from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class NameStatusRecord:
    status: str
    paths: tuple[str, ...]


def _is_ai_path(path: str) -> bool:
    return path == ".ai" or path.startswith(".ai/")


def parse_name_status_z(raw: bytes) -> tuple[NameStatusRecord, ...]:
    """Parse `git diff --name-status -z` output, including rename/copy endpoints."""
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()

    records: list[NameStatusRecord] = []
    index = 0
    while index < len(fields):
        token = fields[index].decode("utf-8", "surrogateescape")
        index += 1

        if "\t" in token:
            status, first_path = token.split("\t", 1)
            paths = [first_path]
        else:
            status = token
            if index >= len(fields):
                raise ValueError(f"missing path for git status {status!r}")
            paths = [fields[index].decode("utf-8", "surrogateescape")]
            index += 1

        if status.startswith(("R", "C")):
            if index >= len(fields):
                raise ValueError(f"missing destination path for git status {status!r}")
            paths.append(fields[index].decode("utf-8", "surrogateescape"))
            index += 1

        records.append(NameStatusRecord(status=status, paths=tuple(paths)))

    return tuple(records)


def violations(records: Iterable[NameStatusRecord]) -> tuple[str, ...]:
    errors: list[str] = []
    for record in records:
        ai_endpoints = [path for path in record.paths if _is_ai_path(path)]
        if ai_endpoints:
            rendered = " -> ".join(record.paths)
            errors.append(f"unauthorized .ai mutation: {record.status} {rendered}")

    return tuple(errors)


def main() -> int:
    try:
        records = parse_name_status_z(sys.stdin.buffer.read())
    except ValueError as exc:
        print(f"invalid git diff --name-status stream: {exc}", file=sys.stderr)
        return 2

    errors = violations(records)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
