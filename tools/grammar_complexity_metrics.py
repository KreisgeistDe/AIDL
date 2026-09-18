#!/usr/bin/env python3
"""Deterministic read-only metrics for the active self-described Core grammar."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from tools.core_language import load_core_authority

GRAMMAR = Path("docs/06-grammar.md")
WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PRODUCTION_START = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\s*=(.*)$")
TERMINAL = re.compile(r'"((?:\\.|[^"\\])*)"')


def ebnf_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading = "(preamble)"
    in_ebnf = False
    fence = None
    block: list[str] = []
    block_heading = heading
    for line in text.splitlines():
        stripped = line.strip()
        if line.startswith("## "):
            heading = line[3:].strip()
        if not in_ebnf and stripped in {"~~~ebnf", "```ebnf"}:
            in_ebnf = True
            fence = "~~~" if stripped.startswith("~~~") else "```"
            block = []
            block_heading = heading
            continue
        if in_ebnf and stripped == fence:
            sections.append((block_heading, "\n".join(block)))
            in_ebnf = False
            fence = None
            continue
        if in_ebnf:
            block.append(line)
    return sections


def productions(sections: list[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    current: str | None = None
    section_name = ""
    pieces: list[str] = []
    for section, block in sections:
        for line in block.splitlines():
            match = PRODUCTION_START.match(line)
            if match:
                if current is not None:
                    result[current] = (section_name, " ".join(pieces).strip())
                current = match.group(1)
                section_name = section
                pieces = [match.group(2).strip()]
            elif current is not None:
                pieces.append(line.strip())
            if current is not None and ";" in line:
                result[current] = (section_name, " ".join(pieces).strip())
                current = None
                pieces = []
    if current is not None:
        result[current] = (section_name, " ".join(pieces).strip())
    return result


def split_top_level_alternatives(rhs: str) -> list[str]:
    result: list[str] = []
    start = 0
    stack: list[str] = []
    quote = False
    escaped = False
    pairs = {")": "(", "]": "[", "}": "{"}
    for index, char in enumerate(rhs):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == '"':
            quote = True
        elif char in "([{":
            stack.append(char)
        elif char in ")]}" and stack and stack[-1] == pairs[char]:
            stack.pop()
        elif char == "|" and not stack:
            result.append(rhs[start:index].strip())
            start = index + 1
    result.append(rhs[start:].strip().rstrip(" ;"))
    return [item for item in result if item]


def measure(path: Path = GRAMMAR, contract_path: Path | None = None) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    sections = ebnf_sections(text)
    prods = productions(sections)
    authority = load_core_authority()
    declaration_kinds = sorted(set(authority.core.contracts) | set(authority.core.aliases))
    terminals: set[str] = set()
    terminal_sections: dict[str, set[str]] = defaultdict(set)
    for section, block in sections:
        for terminal in TERMINAL.findall(block):
            terminals.add(terminal)
            terminal_sections[terminal].add(section)
    alternatives = 0
    signatures: Counter[str] = Counter()
    for _, rhs in prods.values():
        rows = split_top_level_alternatives(rhs)
        alternatives += len(rows)
        for row in rows:
            signatures["block" if '"{"' in row else "structural"] += 1
    return {
        "grammar": str(path),
        "authority": "spec/core-self-description-v1.aidl",
        "contract_revision": None,
        "ebnf_sections": len(sections),
        "productions": len(prods),
        "production_alternatives": alternatives,
        "quoted_terminals_total": len(terminals),
        "top_level_declaration_productions": len(declaration_kinds),
        "concrete_top_level_forms": 0,
        "declaration_productions": declaration_kinds,
        "surface_signatures": len(signatures),
        "surface_signature_counts": dict(sorted(signatures.items())),
        "structural_markers": {},
        "inline_block_dual_productions": [],
        "terminals_by_section": {
            section: {
                "unique_terminals": len({t for t, places in terminal_sections.items() if section in places}),
                "word_terminals": sum(bool(WORD.fullmatch(t)) for t, places in terminal_sections.items() if section in places),
                "symbol_terminals": sum(not bool(WORD.fullmatch(t)) for t, places in terminal_sections.items() if section in places),
            }
            for section, _ in sections
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=GRAMMAR)
    parser.add_argument("--contract", type=Path, default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(measure(args.path, args.contract), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
